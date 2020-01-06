class EventSender:
    __listeners = []

    def emit_event(self, event, message=None):
        for function in self.__listeners:
            function(event, message)

    def add_listener(self, function):
        self.__listeners.append(function)
