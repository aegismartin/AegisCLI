class Scanner_Selector:
    def __init__(self, settings, submodule, target, **kwargs):
        self.submodule = submodule
        self.target = target
        self.settings = settings
        self.kwargs = kwargs  

    def selector(self):
        if self.submodule == 'port':
            from aegiscli.tools.scanner.submodules.port import Port
            script = Port(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target,
                ports=self.kwargs.get("ports") 
            )
            script.result()

        elif self.submodule == 'host':
            from aegiscli.tools.scanner.submodules.host import Host
            script = Host(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target,
            )
            script.result()
