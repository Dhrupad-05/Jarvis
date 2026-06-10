from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from computer_control.models import ActionPlan, ActionType, ResolutionStrategy, ResolvedTarget, TargetType
from computer_control.text import normalize_target, title_name


IRREGULAR_DOMAINS = {
    "huggingface": "huggingface.co",
    "stackoverflow": "stackoverflow.com",
    "geeksforgeeks": "geeksforgeeks.org",
    "x": "x.com",
    "twitter": "x.com",
}


@dataclass(frozen=True, slots=True)
class WebsiteResolver:
    def resolve(self, plan: ActionPlan) -> ResolvedTarget | None:
        target = plan.target_text.strip()
        if plan.action is ActionType.SEARCH:
            return self._search_url(plan)
        if not target:
            return None
        literal = self._literal_url(target)
        if literal:
            return ResolvedTarget(target, TargetType.WEBSITE, literal, ResolutionStrategy.URL_LITERAL, 0.99)
        domain = self._domain_for(target)
        return ResolvedTarget(title_name(target), TargetType.WEBSITE, f"https://{domain}", ResolutionStrategy.DOMAIN_HEURISTIC, 0.72)

    def _search_url(self, plan: ActionPlan) -> ResolvedTarget:
        engine = normalize_target(plan.target_text or "google")
        query = plan.query or ""
        encoded = quote_plus(query)
        if engine == "youtube":
            url = f"https://www.youtube.com/results?search_query={encoded}"
        elif engine == "github":
            url = f"https://github.com/search?q={encoded}"
        elif engine == "kaggle":
            url = f"https://www.kaggle.com/search?q={encoded}"
        else:
            url = f"https://www.google.com/search?q={encoded}"
            engine = "google"
        return ResolvedTarget(engine, TargetType.WEBSITE, url, ResolutionStrategy.SEARCH_ENGINE, 0.95, {"query": query})

    def _literal_url(self, target: str) -> str | None:
        if target.startswith(("http://", "https://")):
            return target
        if target.startswith("www."):
            return f"https://{target}"
        if re.match(r"^[a-z0-9-]+\.[a-z]{2,}(/.*)?$", target, flags=re.I):
            return f"https://{target}"
        return None

    def _domain_for(self, target: str) -> str:
        key = normalize_target(target)
        if key in IRREGULAR_DOMAINS:
            return IRREGULAR_DOMAINS[key]
        return f"www.{key}.com"
