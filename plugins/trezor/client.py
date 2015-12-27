from sys import stderr

from electrum.i18n import _


class GuiMixin(object):
    # Requires: self.proto, self.device

    def callback_ButtonRequest(self, msg):
        if msg.code == 3:
            message = _("Confirm transaction outputs on %s device to continue")
        elif msg.code == 8:
            message = _("Confirm transaction fee on %s device to continue")
        elif msg.code == 7:
            message = _("Confirm message to sign on %s device to continue")
        elif msg.code == 10:
            message = _("Confirm address on %s device to continue")
        else:
            message = _("Check %s device to continue")

        if msg.code in [3, 8] and hasattr(self, 'cancel'):
            cancel_callback = self.cancel
        else:
            cancel_callback = None

        self.handler.show_message(message % self.device, cancel_callback)
        return self.proto.ButtonAck()

    def callback_PinMatrixRequest(self, msg):
        if msg.type == 1:
            msg = _("Please enter %s current PIN")
        elif msg.type == 2:
            msg = _("Please enter %s new PIN")
        elif msg.type == 3:
            msg = _("Please enter %s new PIN again")
        else:
            msg = _("Please enter %s PIN")
        pin = self.handler.get_pin(msg % self.device)
        if not pin:
            return self.proto.Cancel()
        return self.proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, req):
        msg = _("Please enter your %s passphrase")
        passphrase = self.handler.get_passphrase(msg % self.device)
        if passphrase is None:
            return self.proto.Cancel()
        return self.proto.PassphraseAck(passphrase=passphrase)

    def callback_WordRequest(self, msg):
        # TODO
        stderr.write("Enter one word of mnemonic:\n")
        stderr.flush()
        word = raw_input()
        return self.proto.WordAck(word=word)


def trezor_client_class(protocol_mixin, base_client, proto):
    '''Returns a class dynamically.'''

    class TrezorClient(protocol_mixin, GuiMixin, base_client):

        def __init__(self, transport, device):
            base_client.__init__(self, transport)
            protocol_mixin.__init__(self, transport)
            self.proto = proto
            self.device = device

        def call_raw(self, msg):
            try:
                return base_client.call_raw(self, msg)
            except:
                self.bad = True
                raise

    return TrezorClient