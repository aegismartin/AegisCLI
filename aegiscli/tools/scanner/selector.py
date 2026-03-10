class Scanner_Selector:
    def __init__(self, settings, submodule, target, **kwargs):
        self.submodule = submodule
        self.target = target
        self.settings = settings
        self.kwargs = kwargs  # {"ports": "1-80"}

    def selector(self):
        if self.submodule == 'port':
            import aegiscli.tools.scanner.submodules.port as port
            script = port.Port(
                settings=self.settings,
                submodule=self.submodule,
                target=self.target,
                ports=self.kwargs.get("ports")  # cleanly pulls ports out
            )
            script.result()