import pytest

import mfclib
from mfclib.configuration import Config, get_configuration


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
