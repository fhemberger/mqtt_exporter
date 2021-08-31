"""
Additions and enhancements to the prometheus_client package
"""

import prometheus_client as prometheus

class CounterAbsolute(prometheus.Counter):
    """
    CounterAbsolute allows to set the Counter by an absolute value like Gauge, but data is 
    handled properly if counter resets or over flows.
    CounterAbsolute is typically used if values need to by proxied from another source e.g. 
    a network counter, SMTP or MQTT data which return increasing but absolute numbers 
    instead of a diff.

    As Counter must not decrease, setting CounterAbsolute to a lower value is handled as follows:
    A counter overflow or a reset is assumed and the create timestamp gets reset and internally 
    a new Value object created.

    An example for a CounterAbsolute:
        from prometheus_client import Counter
        c = CounterAbsolute('my_failures_total', 'Description of counter')
        c.set(1123.63213)  # set to a absoluter value, if lower than last value Counter gets reset.

    """
    _type = 'counter'


    def set(self, value, fail_on_decrease=False):
        """Increment counter to the given amount."""
        self._raise_if_not_observable()
        if value < 0:
            raise ValueError('Counters can be a positive number only.')
        if value >= self._value.get():
            self._value.set(float(value))
        else:
            if fail_on_decrease:
                raise ValueError(f"Counter must increase {value} lower {self._value.get()}")
            else:
                self._metric_init()
                self._value.set(float(value))
