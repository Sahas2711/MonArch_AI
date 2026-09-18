from dataclasses import dataclass
from pathlib import Path


@dataclass
class PolicyPack:
    name: str
    policy_dir: Path
    corpus_dir: Path          # legal reference text for RAG grounding
    action_template: str      # prompt template for the action/drafting agent

    @classmethod
    def load(cls, name: str) -> "PolicyPack":
        base = Path("policy_packs") / name
        template_file = base / "action_template.txt"
        action_template = template_file.read_text() if template_file.exists() else ""
        return cls(
            name=name,
            policy_dir=base,
            corpus_dir=base / "corpus",
            action_template=action_template,
        )
