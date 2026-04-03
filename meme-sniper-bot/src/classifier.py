"""LLM-powered post classifier for meme token calls."""

import logging
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import anthropic

from src.utils import extract_solana_ca, extract_token_name, extract_dex_url

logger = logging.getLogger("sniper.classifier")


class Classification(Enum):
    FRESH_BUY = "FRESH_BUY"
    DIP_ADD = "DIP_ADD"
    UPDATE = "UPDATE"
    NOISE = "NOISE"


@dataclass
class ClassifierResult:
    classification: Classification
    token_name: Optional[str] = None
    contract_address: Optional[str] = None
    dex_url: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


SYSTEM_PROMPT = """You are a crypto trading signal classifier. Analyze Telegram group messages and classify them.

CLASSIFICATIONS:
- FRESH_BUY: A NEW token call. The poster is entering a position for the first time and sharing it. Contains a contract address or DexScreener link. Language: "aped", "buying", "top here", "blasted", "smol size", "mid-term hold", "bought".
- DIP_ADD: The poster is adding to an EXISTING position on a dip. References buying more of a token they previously called. Still actionable.
- UPDATE: A progress update on an existing position. References prior profits ("$600k -> $2.4M"), past calls ("our 8x call on $TOKEN"), asks for engagement ("smash those reacts"), or celebrates gains. NOT actionable.
- NOISE: Anything else — general chat, memes without calls, questions, etc.

KEY SIGNALS FOR UPDATE (not fresh):
- Dollar profit figures: "$X -> $Y"
- Multiplier references on this token: "3x profits so far", "already up 5x"
- "we were already in", "we bought the pico bottom"
- "if you missed our call on"
- Asking for reactions/engagement
- No new contract address (just token name reference)

KEY SIGNALS FOR FRESH_BUY:
- Contract address present (Solana base58, 32-44 chars)
- DexScreener or Birdeye link
- First-time language: "aped this", "buying top here", "just entered"
- New token introduction with reasoning

Respond with ONLY valid JSON:
{
  "classification": "FRESH_BUY|DIP_ADD|UPDATE|NOISE",
  "token_name": "TOKEN or null",
  "contract_address": "address or null",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}"""


class PostClassifier:
    """Classify Telegram posts as trading signals."""

    def __init__(self, config: dict, position_checker=None):
        """
        Args:
            config: Full config dict
            position_checker: Callable(ca) -> bool, checks if position exists
        """
        self.config = config
        self.position_checker = position_checker
        classifier_cfg = config.get("classifier", {})
        api_key = classifier_cfg.get("api_key", "")
        self.model = classifier_cfg.get("model", "claude-sonnet-4-20250514")
        
        # Strip provider prefix if present
        if "/" in self.model:
            self.model = self.model.split("/", 1)[1]
        
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def _pre_filter(self, text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Regex pre-filter to extract CA, token name, and dex URL.
        
        Returns (contract_address, token_name, dex_url).
        """
        ca = extract_solana_ca(text)
        token = extract_token_name(text)
        dex = extract_dex_url(text)
        return ca, token, dex

    def _has_update_signals(self, text: str) -> bool:
        """Quick check for strong update signals."""
        update_patterns = [
            r"\$[\d,.]+k?\s*->\s*\$[\d,.]+[kKmM]?",  # $600k -> $2.4M
            r"\d+x\s+(?:profits?|gains?|so far|already)",  # 3x profits so far
            r"(?:we|already)\s+(?:were|bought|entered)\s+(?:already|in|the)",  # we were already in
            r"if\s+you\s+missed\s+(?:our|the)\s+.*call",  # if you missed our call
            r"(?:smash|show)\s+(?:those|some)\s+(?:reac|love)",  # smash those reacts
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in update_patterns)

    async def classify(self, text: str) -> ClassifierResult:
        """Classify a Telegram message.
        
        Uses regex pre-filter first, then LLM for ambiguous cases.
        """
        # Step 1: Extract basic signals
        ca, token_name, dex_url = self._pre_filter(text)

        # Step 2: No CA found = NOISE (skip LLM)
        if not ca:
            logger.debug(f"No CA found, classifying as NOISE")
            return ClassifierResult(
                classification=Classification.NOISE,
                token_name=token_name,
                reason="No contract address found",
                confidence=0.9,
            )

        # Step 3: Check for strong update signals with regex
        if self._has_update_signals(text):
            # Check if we have a position — if so, it's definitely an update
            is_existing = False
            if self.position_checker and ca:
                is_existing = self.position_checker(ca)

            if is_existing:
                logger.info(f"Update signal detected for existing position: {ca[:12]}...")
                return ClassifierResult(
                    classification=Classification.UPDATE,
                    token_name=token_name,
                    contract_address=ca,
                    dex_url=dex_url,
                    reason="Profit update on existing position",
                    confidence=0.95,
                )

        # Step 4: CA found — use LLM to classify
        if self.client:
            return await self._llm_classify(text, ca, token_name, dex_url)
        else:
            # Fallback: CA present + no update signals = likely fresh buy
            return self._heuristic_classify(text, ca, token_name, dex_url)

    async def _llm_classify(
        self, text: str, ca: str, token_name: Optional[str], dex_url: Optional[str]
    ) -> ClassifierResult:
        """Use LLM for classification."""
        try:
            # Add position context
            position_context = ""
            if self.position_checker and ca:
                if self.position_checker(ca):
                    position_context = (
                        f"\n\nNOTE: We already have an active position for contract "
                        f"address {ca}. If this is a new buy recommendation for the "
                        f"same token, classify as DIP_ADD."
                    )
                else:
                    position_context = (
                        f"\n\nNOTE: We do NOT have an existing position for contract "
                        f"address {ca}."
                    )

            user_msg = f"Classify this message:{position_context}\n\n---\n{text}\n---"

            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            result_text = response.content[0].text.strip()
            
            # Parse JSON response
            # Handle potential markdown wrapping
            if result_text.startswith("```"):
                result_text = re.sub(r"```(?:json)?\s*", "", result_text)
                result_text = result_text.rstrip("`").strip()

            data = json.loads(result_text)

            classification = Classification(data["classification"])
            
            return ClassifierResult(
                classification=classification,
                token_name=data.get("token_name") or token_name,
                contract_address=ca,
                dex_url=dex_url,
                confidence=float(data.get("confidence", 0.8)),
                reason=data.get("reason", ""),
            )

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, falling back to heuristic")
            return self._heuristic_classify(text, ca, token_name, dex_url)

    def _heuristic_classify(
        self, text: str, ca: str, token_name: Optional[str], dex_url: Optional[str]
    ) -> ClassifierResult:
        """Fallback heuristic classification when LLM is unavailable."""
        text_lower = text.lower()

        # Strong update signals
        if self._has_update_signals(text):
            return ClassifierResult(
                classification=Classification.UPDATE,
                token_name=token_name,
                contract_address=ca,
                dex_url=dex_url,
                confidence=0.7,
                reason="Heuristic: update language detected",
            )

        # Fresh buy signals
        fresh_signals = [
            "aped", "aping", "buying", "bought", "entered",
            "top here", "blasted", "smol size", "mid-term",
            "just entered", "new position", "loading up",
        ]
        has_fresh = any(sig in text_lower for sig in fresh_signals)

        # Check existing position
        is_existing = False
        if self.position_checker and ca:
            is_existing = self.position_checker(ca)

        if has_fresh and is_existing:
            return ClassifierResult(
                classification=Classification.DIP_ADD,
                token_name=token_name,
                contract_address=ca,
                dex_url=dex_url,
                confidence=0.6,
                reason="Heuristic: buy language + existing position = dip add",
            )
        elif has_fresh:
            return ClassifierResult(
                classification=Classification.FRESH_BUY,
                token_name=token_name,
                contract_address=ca,
                dex_url=dex_url,
                confidence=0.65,
                reason="Heuristic: buy language + CA present",
            )

        # CA present but no clear signals — classify as fresh buy with lower confidence
        if ca and dex_url:
            return ClassifierResult(
                classification=Classification.FRESH_BUY,
                token_name=token_name,
                contract_address=ca,
                dex_url=dex_url,
                confidence=0.5,
                reason="Heuristic: CA + DexScreener present, no clear update signals",
            )

        return ClassifierResult(
            classification=Classification.NOISE,
            token_name=token_name,
            contract_address=ca,
            dex_url=dex_url,
            confidence=0.5,
            reason="Heuristic: insufficient buy/update signals",
        )
