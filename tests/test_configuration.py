import pytest

import mfclib
from mfclib.quantity_type import FlowRateQ, TemperatureQ
from mfclib.models.configuration import Config, get_configuration
from mfclib.models.line import MFCLine


class TestGetConfiguration:
    def test_get_configuration_with_only_lines_defined(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
          - name: MFC 4
            gas: {"NH3": "1%", "He": "*"}
          - name: MFC 5
            gas: {"O2": "*"}
        """
        config_file = tmp_path / ".eurotherm.yaml"
        config_file.write_text(config_content)

        config = get_configuration(filename=config_file)
        assert isinstance(config, Config)
        assert len(config.lines) == 3
        assert config.lines[0].name == "MFC A"
        assert config.lines[0].gas == mfclib.models.Mixture.create({"N2": "*"})
        assert config.lines[1].name == "MFC 4"
        assert config.lines[1].gas == mfclib.models.Mixture.create(
            {"NH3": "1%", "He": "*"}
        )
        assert config.lines[2].name == "MFC 5"
        assert config.lines[2].gas == mfclib.models.Mixture.create({"O2": "*"})

    def test_configuration_with_lines_and_controllers(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
            device:
              mfc: Device/MFC/Brooks01
              calibration: latest
          - name: MFC 4
            gas: {"NH3": "1%", "He": "*"}
            device:
              mfc: Device/MFC/Bronkhorst11
          - name: MFC 5
            gas: {"O2": "*"}
        
        controllers:
          - name: Device/MFC/Brooks01
            info:
              manufacturer: Brooks
              make: 5850E (Analog)
              serial_number: T63185/004
              specifications: "2 L/min Ar, 4 bar"
            calibrations:
              - date: 2024-06-20
                gas:
                  N2: "*"
                temperature: 20 degC
                method: linear
                offset: 0 ml/min
                slope: 2.0 L/min
        
          - name: Device/MFC/Bronkhorst11
            info:
              manufacturer: Bronkhorst
              make: ELFlow Select
              model: F-201CV-500-RGD-33-K
              serial_number: M23215384E
              specifications: "500 L/min N2, 4 bar"
            calibrations:
              - date: 2024-06-20
                gas:
                  N2: "*"
                temperature: 20 degC
                method: linear
                offset: 0 ml/min
                slope: 500 L/min
        """

        config_file = tmp_path / ".eurotherm.yaml"
        config_file.write_text(config_content)

        config = get_configuration(filename=config_file)
        assert isinstance(config, Config)
        assert len(config.lines) == 3
        assert len(config.controllers) == 2

    def test_check_for_duplicated_controller_names(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
            device:
              mfc: Device/MFC/Brooks01
              calibration: latest
          - name: MFC 4
            gas: {"NH3": "1%", "He": "*"}
            device:
              mfc: Device/MFC/Bronkhorst11
          - name: MFC 5
            gas: {"O2": "*"}
        
        controllers:
          - name: Device/MFC/Brooks01
            calibrations: []
          - name: Device/MFC/Brooks01
            calibrations: []
        """

        config_file = tmp_path / ".eurotherm.yaml"
        config_file.write_text(config_content)

        with pytest.raises(
            ValueError, match="Duplicate controller names found: Device/MFC/Brooks01"
        ):
            get_configuration(filename=config_file)

    def test_device_name_in_list_of_controllers(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
            device:
              mfc: Device/MFC/Brooks01
              calibration: latest
          - name: MFC 4
            gas: {"NH3": "1%", "He": "*"}
            device:
              mfc: Device/MFC/Bronkhorst11
          - name: MFC 5
            gas: {"O2": "*"}
            device:
              mfc: Device/MFC/Brooks01
        
        controllers:
          - name: Device/MFC/Brooks01
            calibrations: []
          - name: Device/MFC/Bronkhorst11
            calibrations: []
        """

        config_file = tmp_path / ".eurotherm.yaml"
        config_file.write_text(config_content)

        config = get_configuration(filename=config_file)
        assert isinstance(config, Config)

    def test_device_name_not_in_list_of_controllers(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
            device:
              mfc: Device/MFC/Unknown
              calibration: latest
          - name: MFC 4
            gas: {"NH3": "1%", "He": "*"}
            device:
              mfc: Device/MFC/Bronkhorst11
          - name: MFC 5
            gas: {"O2": "*"}
            device:
              mfc: Device/MFC/Brooks01
        
        controllers:
          - name: Device/MFC/Brooks01
            calibrations: []
          - name: Device/MFC/Bronkhorst11
            calibrations: []
        """

        config_file = tmp_path / ".eurotherm.yaml"
        config_file.write_text(config_content)

        with pytest.raises(
            ValueError, match='MFC device "Device/MFC/Unknown" not found in controllers'
        ):
            get_configuration(filename=config_file)


class TestFlowrateToSetpoint:
    def test_flowrate_to_setpoint_valid(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
            device:
              mfc: Device/MFC/Brooks01
              calibration: latest
          - name: MFC 4
            gas: {"NH3": "1%", "He": "*"}
            device:
              mfc: Device/MFC/Bronkhorst11
              calibration: latest
        
        controllers:
          - name: Device/MFC/Brooks01
            calibrations:
              - date: 2024-06-20
                gas:
                  N2: "*"
                temperature: 20 degC
                method: linear
                offset: 0 ml/min
                slope: 2.0 L/min
          - name: Device/MFC/Bronkhorst11
            calibrations:
              - date: 2024-06-20
                gas:
                  N2: "*"
                temperature: 20 degC
                method: linear
                offset: 0 ml/min
                slope: 500 mL/min
        """
        config_file = tmp_path / ".config.yaml"
        config_file.write_text(config_content)

        config = get_configuration(filename=config_file)

        line = config.lines[0]
        flowrate = FlowRateQ(1, "L/min")
        temperature = TemperatureQ(20, "degC")
        setpoint = config.flowrate_to_setpoint(line, flowrate, temperature)
        assert setpoint.m_as('%') == pytest.approx(50.0)

        line = config.lines[0]
        flowrate = FlowRateQ(1, "L/min")
        temperature = 2 * TemperatureQ(20, "degC").to("K")
        setpoint = config.flowrate_to_setpoint(line, flowrate, temperature)
        assert setpoint.m_as('%') == pytest.approx(25.0)

        line = config.lines[1]
        flowrate = FlowRateQ(0.2, "L/min")
        temperature = TemperatureQ(20, "degC")
        setpoint = config.flowrate_to_setpoint(line, flowrate, temperature)
        assert setpoint.m_as('%') == pytest.approx(29.09, abs=0.01)

    def test_flowrate_to_setpoint_line_without_device(self, tmp_path):
        config_content = """
        lines:
          - name: MFC A
            gas: {"N2": "*"}
            device:
              mfc: Device/MFC/Brooks01
              calibration: latest
        
        controllers:
          - name: Device/MFC/Brooks01
            calibrations:
              - date: 2024-06-20
                gas:
                  N2: "*"
                temperature: 20 degC
                method: linear
                offset: 0 ml/min
                slope: 2.0 L/min
        """
        config_file = tmp_path / '.config.yaml'
        config_file.write_text(config_content)

        config = get_configuration(filename=config_file)
        line = MFCLine(name='Invalid Line', gas={'N2': '*'}, device=None)
        flowrate = FlowRateQ(1, 'L/min')
        temperature = TemperatureQ(20, 'degC')

        setpoint = config.flowrate_to_setpoint(line, flowrate, temperature)
        assert setpoint is None
