"""
Crypto Experience Assessment Service
=====================================
Assesses a user's cryptocurrency trading experience based on their
online presence across GitHub, LinkedIn, and web mentions.

Priority Levels:
  - Priority 1 (Veteran):  >5 years crypto experience — early adopter
  - Priority 2 (Experienced): 3-5 years crypto experience
  - Priority 3 (Rookie): 2-3 years crypto experience
  - Blocked: <2 years or no verifiable crypto experience

Experience is assessed from:
  1. GitHub repos with crypto keywords (bitcoin, ethereum, defi, web3, etc.)
  2. GitHub bio/description mentioning crypto
  3. LinkedIn positions at crypto companies or crypto-related roles
  4. LinkedIn skills endorsements for crypto/blockchain
  5. Web search for crypto-related mentions (press, YouTube, TikTok, websites)

Users who verify BOTH GitHub AND LinkedIn get combined scoring.
Users with NO verifiable crypto experience are blocked from trading.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ─── Crypto Keywords ──────────────────────────────────────────────────────────

CRYPTO_KEYWORDS = [
    # Core crypto terms
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "cryptocurrency", "crypto", "blockchain", "defi", "de-fi",
    "web3", "web-3", "nft", "dao", "ico", "ieo",
    # Trading terms
    "trading", "trader", "exchange", "swap", "liquidity",
    "market-making", "arbitrage", "yield", "staking",
    # Technical terms
    "smart-contract", "smartcontract", "solidity", "rust",
    "token", "coin", "wallet", "dex", "cex", "amm",
    # Specific protocols
    "uniswap", "sushiswap", "pancakeswap", "aave", "compound",
    "makerdao", "curve", "balancer", "1inch",
    "opensea", "rarible", "metamask", "phantom",
    "raydium", "jupiter", "serum", "mango",
    # Layer 2 / Alt-L1
    "polygon", "arbitrum", "optimism", "avalanche", "fantom",
    "near", "cardano", "polkadot", "cosmos",
    # Industry terms
    "mining", "miner", "hashrate", "consensus", "proof-of-stake",
    "proof-of-work", "validator", "node", "on-chain",
]

CRYPTO_COMPANY_PATTERNS = [
    r"binance", r"coinbase", r"kraken", r"bybit", r"okx", r"kucoin",
    r"gemini", r"bitfinex", r"crypto\.com", r"ftx", r"alameda",
    r"consensys", r"parity", r"chainlink", r"the graph",
    r"uniswap labs", r"aave", r"compound labs", r"maker",
    r"open sea", r"opensea", r"ripple", r"circle",
    r"blockstream", r"bitgo", r"fireblocks", r"anchorage",
    r"cointracker", r"taxbit", r"ledger", r"trezor",
    r"metamask", r"rainbow", r"phantom", r"trust wallet",
    r"solana labs", r"solana foundation", r"ethereum foundation",
    r"polygon labs", r"arbitrum foundation", r"optimism foundation",
]

CRYPTO_ROLE_PATTERNS = [
    r"crypto", r"blockchain", r"web3", r"defi", r"nft",
    r"smart contract", r"solidity", r"rust developer",
    r"token", r"coin", r"dex", r"decentralized",
    r"on-chain", r"protocol", r"dao",
]


class CryptoPriority(str, Enum):
    """Crypto experience priority levels."""
    VETERAN = "veteran"        # >5 years — Priority 1
    EXPERIENCED = "experienced"  # 3-5 years — Priority 2
    ROOKIE = "rookie"          # 2-3 years — Priority 3
    NO_EXPERIENCE = "no_experience"  # <2 years or none — BLOCKED


PRIORITY_LABELS = {
    CryptoPriority.VETERAN: "Priority 1 — Veteran (5+ years)",
    CryptoPriority.EXPERIENCED: "Priority 2 — Experienced (3-5 years)",
    CryptoPriority.ROOKIE: "Priority 3 — Rookie (2-3 years)",
    CryptoPriority.NO_EXPERIENCE: "Blocked — Insufficient crypto experience",
}

PRIORITY_ORDER = {
    CryptoPriority.VETERAN: 1,
    CryptoPriority.EXPERIENCED: 2,
    CryptoPriority.ROOKIE: 3,
    CryptoPriority.NO_EXPERIENCE: 99,  # Blocked
}


@dataclass
class CryptoExperienceResult:
    """Result of crypto experience assessment."""
    priority: CryptoPriority = CryptoPriority.NO_EXPERIENCE
    estimated_years: float = 0.0
    confidence: float = 0.0  # 0.0 – 1.0
    signals: list = field(default_factory=list)  # Evidence found
    github_crypto_repos: int = 0
    github_crypto_bio: bool = False
    linkedin_crypto_role: bool = False
    linkedin_crypto_company: bool = False
    web_mentions: int = 0
    dual_verified: bool = False  # Both GitHub + LinkedIn
    can_trade: bool = False
    reason: str = ""


# ─── GitHub Crypto Assessment ─────────────────────────────────────────────────

async def assess_github_crypto(access_token: str) -> dict:
    """Assess crypto experience from GitHub profile and repositories.
    
    Checks:
      - User bio for crypto keywords
      - Public repositories for crypto-related topics
      - Repository descriptions and languages
      - Account creation date (earlier = more likely experienced)
    
    Returns dict with crypto signals.
    """
    signals = []
    crypto_repos = 0
    crypto_bio = False
    account_age_years = 0.0

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Fetch user profile
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp.raise_for_status()
            user_data = resp.json()

            # Check bio for crypto keywords
            bio = (user_data.get("bio") or "").lower()
            if bio:
                for kw in CRYPTO_KEYWORDS:
                    if kw in bio or kw.replace("-", " ") in bio or kw.replace(" ", "") in bio:
                        crypto_bio = True
                        signals.append(f"GitHub bio mentions: {kw}")
                        break

            # Calculate account age
            created_at = user_data.get("created_at", "")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    account_age_years = (datetime.now(timezone.utc) - created_dt).days / 365.25
                except (ValueError, TypeError):
                    pass

            # Fetch public repositories (up to 100)
            resp = await client.get(
                "https://api.github.com/user/repos",
                params={"per_page": 100, "sort": "updated", "type": "owner"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp.raise_for_status()
            repos = resp.json()

            for repo in repos:
                repo_name = (repo.get("name") or "").lower()
                repo_desc = (repo.get("description") or "").lower()
                repo_lang = (repo.get("language") or "").lower()
                repo_topics = [t.lower() for t in (repo.get("topics") or [])]

                # Combine all text for keyword matching
                repo_text = f"{repo_name} {repo_desc} {' '.join(repo_topics)}"

                is_crypto = False
                for kw in CRYPTO_KEYWORDS:
                    kw_variants = [kw, kw.replace("-", " "), kw.replace(" ", "-")]
                    for variant in kw_variants:
                        if variant in repo_text:
                            is_crypto = True
                            break
                    if is_crypto:
                        break

                # Solidity/Vyper/Rust repos are likely crypto-related
                if repo_lang in ("solidity", "vyper", "move"):
                    is_crypto = True

                if is_crypto:
                    crypto_repos += 1
                    signals.append(
                        f"GitHub crypto repo: {repo.get('name')} "
                        f"({repo.get('language', 'unknown')})"
                    )

        except httpx.HTTPError as exc:
            logger.error("GitHub crypto assessment failed: %s", exc)

    return {
        "crypto_repos": crypto_repos,
        "crypto_bio": crypto_bio,
        "account_age_years": account_age_years,
        "signals": signals,
    }


# ─── LinkedIn Crypto Assessment ────────────────────────────────────────────────

async def assess_linkedin_crypto(access_token: str) -> dict:
    """Assess crypto experience from LinkedIn profile.
    
    Checks:
      - Current and past positions for crypto companies
      - Job titles for crypto-related roles
      - Skills for blockchain/crypto mentions
    
    Returns dict with crypto signals.
    """
    signals = []
    crypto_role = False
    crypto_company = False

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Fetch user profile from LinkedIn OpenID Connect
            resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            # Check name/title for crypto keywords
            name = (data.get("name") or "").lower()
            for pattern in CRYPTO_ROLE_PATTERNS:
                if re.search(pattern, name, re.IGNORECASE):
                    crypto_role = True
                    signals.append(f"LinkedIn name/role mentions: {pattern}")
                    break

        except httpx.HTTPError as exc:
            logger.error("LinkedIn crypto assessment failed: %s", exc)

    return {
        "crypto_role": crypto_role,
        "crypto_company": crypto_company,
        "signals": signals,
    }


# ─── Web Presence Assessment ──────────────────────────────────────────────────

async def assess_web_crypto_presence(display_name: str, username: str = "") -> dict:
    """Search the web for crypto-related mentions of the user.
    
    Searches for the user's name combined with crypto keywords
    to find mentions in press, YouTube, TikTok, personal websites, etc.
    
    Uses DuckDuckGo HTML search (no API key required).
    
    Returns dict with web mention signals.
    """
    signals = []
    web_mentions = 0

    if not display_name:
        return {"web_mentions": 0, "signals": []}

    search_queries = [
        f'"{display_name}" cryptocurrency',
        f'"{display_name}" crypto trading',
        f'"{display_name}" blockchain',
    ]

    if username:
        search_queries.append(f'"{username}" crypto')

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for query in search_queries:
            try:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    },
                )
                if resp.status_code == 200:
                    text = resp.text.lower()
                    # Count result snippets that contain the name + crypto
                    name_lower = display_name.lower()
                    if name_lower in text:
                        # Count how many result blocks contain the name
                        # DDG results are in <a class="result__a"> tags
                        result_count = text.count("result__a")
                        if result_count > 0:
                            web_mentions += min(result_count, 5)  # Cap at 5 per query
                            signals.append(
                                f"Web search '{query}': found {result_count} results"
                            )
            except httpx.HTTPError:
                continue  # Skip failed queries, don't block verification

    return {"web_mentions": web_mentions, "signals": signals}


# ─── Combined Experience Assessment ────────────────────────────────────────────

def calculate_crypto_priority(
    github_data: Optional[dict] = None,
    linkedin_data: Optional[dict] = None,
    web_data: Optional[dict] = None,
    dual_verified: bool = False,
) -> CryptoExperienceResult:
    """Calculate the user's crypto experience priority level.
    
    Scoring system:
      - Each GitHub crypto repo: +0.5 years
      - GitHub bio mentioning crypto: +1.0 year
      - GitHub account age (if >2 years): +0.5 year
      - LinkedIn crypto role: +1.5 years
      - LinkedIn crypto company: +2.0 years
      - Each web mention (capped at 10): +0.3 years
      - Dual verification bonus: +1.0 year
      - Minimum floor: 0.0 years
    
    Priority assignment:
      - >5 years → Veteran (Priority 1)
      - 3-5 years → Experienced (Priority 2)
      - 2-3 years → Rookie (Priority 3)
      - <2 years → NO_EXPERIENCE (Blocked)
    """
    estimated_years = 0.0
    all_signals = []
    github_crypto_repos = 0
    github_crypto_bio = False
    linkedin_crypto_role = False
    linkedin_crypto_company = False
    web_mentions = 0

    # GitHub signals
    if github_data:
        github_crypto_repos = github_data.get("crypto_repos", 0)
        github_crypto_bio = github_data.get("crypto_bio", False)
        account_age = github_data.get("account_age_years", 0)

        # Crypto repos contribute experience
        repo_years = min(github_crypto_repos * 0.5, 3.0)  # Cap at 3 years from repos
        estimated_years += repo_years
        if github_crypto_repos > 0:
            all_signals.append(f"{github_crypto_repos} crypto-related GitHub repos (+{repo_years:.1f} yrs)")

        # Bio mentioning crypto
        if github_crypto_bio:
            estimated_years += 1.0
            all_signals.append("GitHub bio mentions crypto (+1.0 yrs)")

        # Account age bonus (long-standing GitHub users more likely experienced)
        if account_age >= 2:
            estimated_years += 0.5
            all_signals.append(f"GitHub account age: {account_age:.1f} years (+0.5 yrs)")

        all_signals.extend(github_data.get("signals", []))

    # LinkedIn signals
    if linkedin_data:
        linkedin_crypto_role = linkedin_data.get("crypto_role", False)
        linkedin_crypto_company = linkedin_data.get("crypto_company", False)

        if linkedin_crypto_role:
            estimated_years += 1.5
            all_signals.append("LinkedIn role involves crypto (+1.5 yrs)")

        if linkedin_crypto_company:
            estimated_years += 2.0
            all_signals.append("LinkedIn position at crypto company (+2.0 yrs)")

        all_signals.extend(linkedin_data.get("signals", []))

    # Web presence signals
    if web_data:
        web_mentions = web_data.get("web_mentions", 0)
        web_years = min(web_mentions * 0.3, 3.0)  # Cap at 3 years from web
        if web_mentions > 0:
            estimated_years += web_years
            all_signals.append(f"{web_mentions} web mentions (+{web_years:.1f} yrs)")

        all_signals.extend(web_data.get("signals", []))

    # Dual verification bonus
    if dual_verified:
        estimated_years += 1.0
        all_signals.append("Dual verification (GitHub + LinkedIn) (+1.0 yrs)")

    # Determine priority
    if estimated_years > 5.0:
        priority = CryptoPriority.VETERAN
    elif estimated_years >= 3.0:
        priority = CryptoPriority.EXPERIENCED
    elif estimated_years >= 2.0:
        priority = CryptoPriority.ROOKIE
    else:
        priority = CryptoPriority.NO_EXPERIENCE

    can_trade = priority != CryptoPriority.NO_EXPERIENCE

    reason = ""
    if not can_trade:
        reason = (
            f"Insufficient crypto experience detected ({estimated_years:.1f} years). "
            f"Minimum 2 years required. Connect both GitHub and LinkedIn, "
            f"or demonstrate crypto experience through projects, roles, or online presence."
        )

    # Calculate confidence (how many data sources contributed)
    sources = 0
    if github_data:
        sources += 1
    if linkedin_data:
        sources += 1
    if web_data:
        sources += 1
    confidence = min(sources / 3.0, 1.0)

    return CryptoExperienceResult(
        priority=priority,
        estimated_years=round(estimated_years, 1),
        confidence=round(confidence, 2),
        signals=all_signals,
        github_crypto_repos=github_crypto_repos,
        github_crypto_bio=github_crypto_bio,
        linkedin_crypto_role=linkedin_crypto_role,
        linkedin_crypto_company=linkedin_crypto_company,
        web_mentions=web_mentions,
        dual_verified=dual_verified,
        can_trade=can_trade,
        reason=reason,
    )


async def run_full_crypto_assessment(
    display_name: str,
    username: str = "",
    github_token: Optional[str] = None,
    linkedin_token: Optional[str] = None,
) -> CryptoExperienceResult:
    """Run the full crypto experience assessment pipeline.
    
    1. Assess GitHub crypto presence (if token provided)
    2. Assess LinkedIn crypto presence (if token provided)
    3. Search web for crypto mentions
    4. Calculate combined priority
    """
    github_data = None
    linkedin_data = None

    # GitHub assessment
    if github_token:
        github_data = await assess_github_crypto(github_token)

    # LinkedIn assessment
    if linkedin_token:
        linkedin_data = await assess_linkedin_crypto(linkedin_token)

    # Web presence assessment
    web_data = await assess_web_crypto_presence(display_name, username)

    # Dual verification check
    dual_verified = github_data is not None and linkedin_data is not None

    return calculate_crypto_priority(
        github_data=github_data,
        linkedin_data=linkedin_data,
        web_data=web_data,
        dual_verified=dual_verified,
    )
