from __future__ import division, absolute_import, print_function, unicode_literals

# USB2 driver uses direct USB connection. Requires PyUSB
import usb.core
from usb.util import (find_descriptor, claim_interface, endpoint_direction, ENDPOINT_OUT, ENDPOINT_IN)

from ant.core.exceptions import DriverError
import ant.core.driver

class USB2Driver(ant.core.driver.USB2Driver):
    def _open(self):
        # Most of this is straight from the PyUSB example documentation
        dev = usb.core.find(idVendor=self.idVendor, idProduct=self.idProduct,
                            custom_match=lambda d: (d.bus == self.bus or self.bus is None) and
                                                   (d.address == self.address or self.address is None))

        if dev is None:
            raise DriverError("Could not open device (not found)")

        # make sure the kernel driver is not active
        try:
            if dev.is_kernel_driver_active(0):
                try:
                    dev.detach_kernel_driver(0)
                except usb.core.USBError as e:
                    exit("could not detach kernel driver: {}".format(e))
        except NotImplementedError:
            pass  # for non unix systems

        dev.set_configuration()
        cfg = dev.get_active_configuration()

        intf = cfg[(0, 0)]

        claim_interface(dev, intf)

        endpoint_out_matcher = \
            lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT
        epOut = find_descriptor(intf, custom_match=endpoint_out_matcher)
        assert epOut is not None

        endpoint_in_matcher = \
            lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
        ep_in = find_descriptor(intf, custom_match=endpoint_in_matcher)
        assert ep_in is not None

        self._epOut = epOut
        self._epIn = ep_in
        self._dev = dev
        self._intNum = intf