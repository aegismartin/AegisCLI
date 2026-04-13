class Profiler_Selector:
    def __init__(self, settings, submodule, target):
        self.submodule = submodule
        self.target = target
        self.settings = settings

    def selector(self):
        if self.submodule == 'whois':
            from aegiscli.tools.profiler.submodules.whois import Whois
            script = Whois(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target
            )
            script.result()
            
        elif self.submodule == 'dns':
            from aegiscli.tools.profiler.submodules.dns_module import DNS
            script = DNS(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target
            )
            script.result()
        elif self.submodule == 'web':
            from aegiscli.tools.profiler.submodules.web import WebFinger
            script = WebFinger(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target
            )
            script.result()
        else:
            raise ValueError(f"Unknown submodule: {self.submodule}")