class Profiler_Selector:
    def __init__(self, settings, submodule, target):
        self.submodule = submodule
        self.target = target
        self.settings = settings

    def selector(self):
        if self.submodule == 'whois':
            import aegiscli.tools.profiler.submodules.whois as whois
            script = whois.Whois(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target
            )
            script.result()
            
        elif self.submodule == 'dns':
            import aegiscli.tools.profiler.submodules.dns_module as dns_module
            script = dns_module.DNS(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target
            )
            script.result()
        elif self.submodule == 'web':
            import aegiscli.tools.profiler.submodules.web as web
            script = web.WebFinger(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target
            )
            script.result()
