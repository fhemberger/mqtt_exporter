"""
Pytest for prometheus client enhancements
"""
import os
import logging
import time
import pytest
from utils.prometheus_additions import CounterAbsolute
import prometheus_client as prometheus

logging.basicConfig(level=logging.DEBUG)

TMP_DIR=os.path.join(
    os.path.dirname(__file__),
    'tmp_data'
)
DATA_DIR=os.path.join(
    os.path.dirname(__file__),
    'test_data'
)

@pytest.fixture(scope="class")
def get_registry():
    yield prometheus.REGISTRY
    # reset prometheus registry between tests
    collectors = list(prometheus.REGISTRY._collector_to_names.keys())
    for collector in collectors:
        prometheus.REGISTRY.unregister(collector)

old_creation_time = 0.0

class TestCounterWithReset:
    a_counter_absolute = CounterAbsolute('Absolute_Counter', 'Test metric' )
    old_creation_time = 0.0
    param_test_data_sets = [
        (10, False),
        (10, True),
        (11, True),
        (110, True),
        (110, True),
        (210, True),
        (310.7, True),
        (110, False),
        (210, True),
        (310.7, True),
    ]

    @pytest.mark.parametrize("value, same_creation_time", param_test_data_sets)
    def test_counter_absolute(self, request, get_registry, value, same_creation_time):
        global old_creation_time
        self.a_counter_absolute.set(value)
        creation_time = self.a_counter_absolute._created
        logging.info(f"Creation time: {creation_time:e}")
        registry = get_registry
        registry.collect()
        prometheus.write_to_textfile(os.path.join(TMP_DIR, f"absolute_counter_{request.node.callspec.id}_{value:05}.txt"), prometheus.REGISTRY)

        assert self.a_counter_absolute._value.get() == value
        assert (creation_time == old_creation_time ) == same_creation_time
        old_creation_time = creation_time
        time.sleep(0.005)


class TestCounterRestForbidden:
    a_counter_absolute = CounterAbsolute('Strict_Absolute_Counter', "This Counters doesn't allow reset")

    def test_counter_reset(self):
        val_first = 0.3324234
        val_second = 0.3324233
        self.a_counter_absolute.set(val_first, fail_on_decrease=True)
        with pytest.raises(ValueError, match=rf"Counter must increase {val_second} lower {val_first}"):
            self.a_counter_absolute.set(val_second, fail_on_decrease=True)
