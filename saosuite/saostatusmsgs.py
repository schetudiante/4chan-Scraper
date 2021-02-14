from sys import stdout

################################################################################

class IdempotentlyFinished():
    def __init__(self):
        self.active = True

    @staticmethod
    def init(method):
        def decorated(self, *args, **kwargs):
            self.active = True
            return method(self, *args, **kwargs)
        return decorated

    @staticmethod
    def requireActive(method):
        # to prevent calling once an instance has had self.finish() / @deactivate method called: idempotent finishing of instances
        def decorated(self, *args, **kwargs):
            if self.active:
                return method(self, *args, **kwargs)
        return decorated

    @staticmethod
    def deactivate(method):
        def decorated(self, *args, **kwargs):
            return_value = method(self, *args, **kwargs)
            self.active = False
            return return_value
        return decorated

################################################################################

class ProgressMessage():
    """Progress message: message with progress bar and counter. This version is a use-once instance; progressmsg is recyclable"""
    @IdempotentlyFinished.init
    def __init__(self, message = None, position = 0, of = 1, endMessage = None, progressBarLength = 10, useUnicodeBlocks = False):
        self.message = message or ""
        self.position = position
        self.of = of
        self.endMessage = endMessage or ""
        self.useUnicodeBlocks = useUnicodeBlocks
        self.progressBarLength = progressBarLength

        self._generateProgressText()
        stdout.write("{}{}".format(self.message, self.progressText))
        stdout.flush()

    def _generateProgressText(self):
        if self.useUnicodeBlocks:
            numberOfHalfBars = int(2 * self.progressBarLength * (self.position / self.of))
            barsAndSpaces = "{}{}".format("\u2588" * int(numberOfHalfBars / 2), ("\u258C" if numberOfHalfBars % 2 else "")).ljust(self.progressBarLength, " ")
            self.progressText = "|{}| ({}/{})".format(barsAndSpaces, self.position, self.of)
        else:
            hashesAndUnderscores = ("#" * int(self.progressBarLength * (self.position / self.of))).ljust(self.progressBarLength, "_")
            self.progressText = "[{}] ({}/{})".format(hashesAndUnderscores , self.position, self.of)

    @IdempotentlyFinished.requireActive
    def printMessage(self, message):
        stdout.write("\r{}\n".format(message.ljust(len(self.message) + len(self.progressText), " ")))
        stdout.write("{}{}".format(self.message, self.progressText))
        stdout.flush()

    @IdempotentlyFinished.requireActive
    def tick(self, times = 1, endMessage = None):
        if endMessage is not None:
            self.endMessage = endMessage
        stdout.write("\b" * len(self.progressText))
        self.position = min([self.position + times, self.of])
        self._generateProgressText()
        stdout.write(self.progressText)
        stdout.flush()
        if self.position == self.of:
            self.finish()

    @IdempotentlyFinished.requireActive
    @IdempotentlyFinished.deactivate
    def finish(self, endMessage = None):
        if endMessage is not None:
            self.endMessage = endMessage
        stdout.write(self.endMessage)
        stdout.write("\n")
        stdout.flush()
