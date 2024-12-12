import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

import pandas as pd
import pint

from ..models.configuration import DataLoggingConfig

logger = logging.getLogger(__name__)


class FileDataLogger:
    def __init__(self, cfg: DataLoggingConfig):
        self.cfg = cfg
        self.last_rotation: datetime = datetime.now()
        self.current_file: Optional[Path] = None

    def log_data(self, data: pd.DataFrame):
        self._ensure_file()
        lines = self._build_lines(data)
        self._write(lines)

    def _build_lines(self, data: pd.DataFrame):
        # select columns
        df = data[self.cfg.columns]

        # iterate over rows
        for row in df.itertuples():
            yield self._format_line(row._asdict())

    def _format_line(self, values: Mapping[str, Any]):
        values = [self._format_value(key, values[key]) for key in self.cfg.columns]
        return self._join_columns(values)

    def _format_value(self, key: str, value):
        if key in self.cfg.units:
            units = self.cfg.units[key]
            value = value.m_as(units)

        if isinstance(value, str):
            return value
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return self.cfg.format % value

    def _join_columns(self, values: List[str]):
        return self.cfg.separator.join(values)

    def _write(self, lines: Iterable[str]):
        with open(self.current_file, mode='a', encoding='utf-8') as file:
            for line in lines:
                file.write(f'{line}\n')

    def _ensure_file(self):
        # current time
        now = datetime.now()

        # time elapsed after last rotation
        elapsed = now - self.last_rotation
        if elapsed > self.cfg.rotate_every.to_timedelta():
            time = pint.Quantity(float(elapsed.seconds), 's').to(
                self.cfg.rotate_every.units
            )
            logger.info(f'[log] {time:.4~P} elapsed since last file rotation')
            # we need to create a new file
            self.last_rotation = now
            self.current_file = None

        if self.current_file is None:
            # create directory, if necessary
            path = Path(self.cfg.directory.format(now))
            if not path.exists():
                path.mkdir(parents=True)

            # build file path
            filename = self.cfg.filename.format(now)
            self.current_file = path / filename
            logger.info(f'[log] New data log file: {self.current_file}')

            # log header
            header = self._join_columns(self.cfg.columns)
            self._write([header])
