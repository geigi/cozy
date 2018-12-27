class EventSender:
    # Contains all listeners
    __listeners = []
    def emit_event(self, event, message=None):
        """
        This function is used to notify listeners of ui state changes.
        """
        for function in self.__listeners:
            function(event, message)

    def add_listener(self, function):
        """
        Add a listener to listen to changes from the io.
        """
        self.__listeners.append(function)