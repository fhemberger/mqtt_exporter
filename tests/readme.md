# Tests with pytest

make sure pytest is installed `pip install -r requirements-dev.txt` 
run `pytest -s -o log_cli=true` from the repository root  

## test_mqtt_explorer.py:test_update_metrics

This test loads test mqtt data from a file and feeds it into mqtt_exporter and check if expected results are recorded in the prometheus client.

### directory structure
Test data is loaded from following directory structure:

```
./tests/
    ./test_data/
        ./test1/
            conf.yaml
            mqtt_msg.csv
        ./test2/
            conf.yaml
            mqtt_msg.csv
        ./test_xyz/
            conf.yaml
            mqtt_msg.csv
   ./tmp_data
        [metric_test...##,txt]
```

In `test-data` each subfolder (e.g. `test1`, `test_bla`) contains a separate set of test data. There is no naming convention for folders. The could be descriptive like `test_for_issue1234`. Avoid any special characters and white spaces.

Files:
- `conf.yaml`: a config like a config for mqtt_exporter itself, but only the `metrics` part and a new optional attribute `timescale` is read from it. 
- `mqtt_msg.csv`: fake mqtt data, format description see below.

`tmp-data` contains prometheus scrape output from after each processed mqtt msg data. This folder will be cleaned before each test run. 

### mqtt_msg.csv file format

`mqtt_msg.csv` is a CSV file with `;` as delimiter and `'` as quotation character. 
Following Column looks are expected:

```
in_topic;in_payload;out_name;out_labels;out_value;delay;assert
```
- `in_topic`: topic as from mqtt server
- `in_payload`: payload from mqtt server as string (will be converted byte array)
- `out_name`: metric name without any suffix like `total`, `sum`, `bucket`, ...
- `out_labels`: labels notes as a JSON string including the topic.
- `out_value`: expected value for simple metrics like gauge it is a number. For other metrics is is a JSON string with expected values per suffix e.g. `{"_count": 10, "_sum": 85.55, "_bucket": 10}`
- `delay`: seconds delay until the next mqtt msg is processed. The `timescale` config attribute speed up/slow down the delay. A time scale of 0 means no default, a timescale of 1 means realtime. Default timescale = 0
- `assert`: `True/False`. Specify if the test should pass or not. In most cases this should be `True`

Metric type `Histogram` special handling here as it will log a `$(metric_name)_bucket` metric for each bucket with a reserved label `le` in the meaning of _less or equal_. Specify `le` for one bucket and set the expected count to the `bucket` attribute in the `out_value` JSON. See examples in `test1`.

For sample data see existing tests above.

### Gather test data from live environment

If logging level is set to `debug` the log will contain some lines that should be already correct formatted to be placed in a `mqtt_msq.csv`.

they look like this:
```
2021-08-08 22:24:36,996 DEBUG: TEST_DATA: fhem/Terrasse/TermPearl02/humidity; 21.0; fhem_humidity_percent; {"location": "paz", "topic": "fhem/paz/TermPearl01/humidity"}; 17.0; 0; True
2021-08-08 22:24:30,601 DEBUG: TEST_DATA: fhem/Terrasse/TerrasseWeiss/humidity; 20.0; fhem_humidity_percent; {"location": "paz", "topic": "fhem/paz/TermPearl01/humidity"}; 17.0; 0; True
2021-08-08 22:24:27,097 DEBUG: TEST_DATA: fhem/Garten/TermFetanten01/temperature; 16.7; fhem_temperature_celsius; {"location": "Terrasse", "topic": "fhem/Terrasse/TerrasseWeiss/temperature"}; 16.0; 0; True
2021-08-08 22:23:58,831 DEBUG: TEST_DATA: fhem/paz/TermPearl01/humidity; 17.0; fhem_humidity_percent; {"location": "paz", "topic": "fhem/paz/TermPearl01/humidity"}; 17.0; 0; True
```
Tips:
- remove `.* DEBUG: TEST_DATA: `.
- Make sure the `mqtt_msg.csv`  contains as first line the headers given above. 
- The captured data won't fit if the `payload/__value__` has been replaced by a label_config. Please set `in_payload` to the correct value manually. An example for this exception is the `- name:     'mqtt_broker_version'` metric from the example configurations. 
- put the data in a new subfolder in the `test_data` dir. Copy also the config file from the live environment to this folder (you should remove the `mqtt` part from it. Make also sure the recorded data don't contain sensitive data).
- Create a PR and share the test data, as this will allow all developers to verify code changes. 

