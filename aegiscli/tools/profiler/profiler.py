from abc import ABC, abstractmethod


class Profiler(ABC):
    def __init__(self, settings: dict | None, submodule: str | None, advanced: bool, target: str):
        # validate target early — no submodule should ever run against a blank target
        if not target or not target.strip():
            raise ValueError("Target cannot be empty")

        self.settings = settings
        self.submodule = submodule
        self.advanced = advanced
        self.target = target.strip()

    @abstractmethod
    def fetch(self):
        """Collect all data required for this tool. Populate class variables."""
        pass

    @abstractmethod
    def display(self):
        """Format and print results to terminal."""
        pass

    @abstractmethod
    def export(self):
        """Serialize results to JSON envelope. Write to disk only if --log is active."""
        pass

    @abstractmethod
    def result(self):
        """Orchestrate the full pipeline: fetch → display → export."""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} target={self.target!r} submodule={self.submodule!r}>"