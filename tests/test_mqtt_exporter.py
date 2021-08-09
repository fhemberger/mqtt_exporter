"""
py test testing for mqtt_exporter

"""

import csv
import distutils.util
import json
from json.decoder import JSONDecodeError
import os
import time
import logging

import prometheus_client as prometheus
import prometheus_client.registry
import mqtt_exporter
import pytest

logging.basicConfig(level=logging.DEBUG)

TMP_DIR=os.path.join(
    os.path.dirname(__file__),
    'tmp_data'
)
DATA_DIR=os.path.join(
    os.path.dirname(__file__),
    'test_data'
)

def setup_module(module): #pylint: disable=unused-argument
    """ setup any state specific to the execution of the given module."""
    delete_temp_test_files()


def delete_temp_test_files():
    # delete TEMP files
    for file in os.listdir(TMP_DIR):
        if file == '.gitkeep':
            continue
        os.remove(os.path.join(TMP_DIR, file))


class MqttCVS:
    in_topic = "in_topic"
    in_payload	= "in_payload"
    out_name = "out_name"
    out_labels = "out_labels"
    out_value = "out_value"
    delay = "delay"
    expected_assert = "assert"

def _get_mqtt_data(file_name):
    """
    Reads mqtt fake data and expected results from file
    """
    mqtt_data = []
    with open(file_name, newline='') as mqtt_data_csv:
        csv_reader = csv.DictReader(mqtt_data_csv, quotechar="'", delimiter=';')
        for row in csv_reader:
            row[MqttCVS.in_topic] = row[MqttCVS.in_topic].strip()
            row[MqttCVS.out_name] = row[MqttCVS.out_name].strip()
            # covert payloud to bytes, as in a MQTT Message
            row[MqttCVS.in_payload] = row[MqttCVS.in_payload].encode('UTF-8')
            # parse labels, to a python object.
            row[MqttCVS.out_labels] = json.loads(row.get(MqttCVS.out_labels, '{}'))
            # Value could be a JSON, a float or anthing else. 
            try: 
                row[MqttCVS.out_value] = float(row.get(MqttCVS.out_value))
            except ValueError:
                try:
                    row[MqttCVS.out_value] = json.loads(row.get(MqttCVS.out_value))
                except (JSONDecodeError, TypeError):
                    pass # leave as it is 
            # set delay to 0 if not a number
            try: 
                row[MqttCVS.delay] = float(row.get(MqttCVS.delay, 0))
            except ValueError:
                row[MqttCVS.delay] = 0
            # convert string to bool for expected assertion. 
            row[MqttCVS.expected_assert] = bool(
                distutils.util.strtobool(row.get(MqttCVS.expected_assert, "True").strip()))
            mqtt_data.append(row)
    return mqtt_data


def _get_test_data():
    """
    Reads test data from DATA_DIR sub directories.
    Each subdirectory is expected to contain a `conf.yaml` file with a metrics config (like in the config file)
    and a CSV file `mqtt_msg.csv` with fake mqtt data ";" delimited:
    `in_topic;in_payload;out_name;out_labels;out_value;delay;assert`
    where 
    lables_out: json string with all expected lables
    delay: delay until the next line is processed 
    assert: expected assert result, True if out_value matches prometheus metric
    """
    test_data_sets = []
    test_data_dirs = [f.path for f in os.scandir(DATA_DIR) if f.is_dir()]
    test_names = [ os.path.basename(os.path.normpath(name)) for name in test_data_dirs]
    for test_data_dir in test_data_dirs:
        conf_file = os.path.join(test_data_dir, 'conf.yaml')
        mqtt_data_file = os.path.join(test_data_dir, 'mqtt_msg.csv')
        if not os.path.isfile(conf_file) or not os.path.isfile(mqtt_data_file):
            logging.error(f"Test data dir {test_data_dir} doesn't contain required files, skipping")
            continue
        config_yaml = mqtt_exporter._read_config(conf_file)
        config_yaml = mqtt_exporter._parse_config_and_add_defaults(config_yaml)
        test_data_sets.append((
                config_yaml['metrics'], 
                _get_mqtt_data(mqtt_data_file),
                config_yaml.get('timescale', 0),
            ))
    return test_names, test_data_sets

def _get_suffixes_by_metric_name(metrics, metric_name):
    metric_type = None
    for _, outer_metric in metrics.items():
        for metric in outer_metric:
            if metric['name'] == metric_name:
                metric_type = metric['type']
                break

    for suffix in mqtt_exporter.SUFFIXES_PER_TYPE[metric_type]:
        if len(suffix) == 0:
            yield suffix
        else:
            yield f"_{suffix}"
    

class FakeMSG():
    """"Simulate MQTT Msg"""
    def __init__(self, topic, payload) -> None:
        self.topic = topic
        self.payload = payload


param_test_data_dirs, param_test_data_sets = _get_test_data()

@pytest.mark.parametrize("metrics,mqtt_data_set,timescale", param_test_data_sets, ids=param_test_data_dirs)
def test_update_metrics(caplog, request, metrics, mqtt_data_set, timescale):
    """
    reads a label_config and some mqtt data and asserts if they are in the metrics
    """
    logging.info(f"Start test_update_metrics with ID {request.node.callspec.id}")

    # reset prometheus registry between tests
    collectors = list(prometheus.REGISTRY._collector_to_names.keys())
    for collector in collectors:
        prometheus.REGISTRY.unregister(collector)

    i = 1
    for mqtt_data in mqtt_data_set:
        msg = FakeMSG(mqtt_data[MqttCVS.in_topic], mqtt_data[MqttCVS.in_payload])
        mqtt_exporter._on_message(None, metrics, msg)
        prometheus.REGISTRY.collect()
        prometheus.write_to_textfile(os.path.join(TMP_DIR, f"metric_{request.node.callspec.id}_{i:02}.txt"), prometheus.REGISTRY)
        # depending on metric type one or more metrics with different suffixes are added. 
        for suffix in _get_suffixes_by_metric_name(metrics, mqtt_data[MqttCVS.out_name]):
            # historgram with buckets need special handling, remove bucket labe label 'le'
            labels = mqtt_data[MqttCVS.out_labels].copy()
            if not suffix == "_bucket" and labels.get('le'):
                labels.pop('le')

            expected_result = mqtt_data[MqttCVS.out_value]
            expected_result = expected_result if not isinstance(expected_result, dict) else expected_result[suffix]
            logging.info(f"Assert {mqtt_data[MqttCVS.out_name]}{suffix} from testdata record {i}")
            assert ( prometheus.REGISTRY.get_sample_value(
                f"{mqtt_data[MqttCVS.out_name]}{suffix}", 
                labels
                ) == expected_result ) == mqtt_data[MqttCVS.expected_assert]
        time.sleep(mqtt_data[MqttCVS.delay] * timescale)
        i += 1
    for record in caplog.records:
        assert record.levelno < logging.ERROR