from __future__ import annotations

from dataclasses import dataclass

from dmm_app.models import InstrumentType, MeasurementFunction


@dataclass(frozen=True)
class MeasurementCommand:
    function: MeasurementFunction
    prepare_commands: tuple[str, ...]
    query_command: str
    unit: str


@dataclass(frozen=True)
class InstrumentProfile:
    instrument: InstrumentType
    idn_query: str
    idn_expected_tokens: tuple[str, ...]
    commands: dict[MeasurementFunction, MeasurementCommand]


INSTRUMENT_PROFILES: dict[InstrumentType, InstrumentProfile] = {
    InstrumentType.MP730889: InstrumentProfile(
        instrument=InstrumentType.MP730889,
        idn_query="*IDN?",
        idn_expected_tokens=("MULTICOMP", "MP730889"),
        commands={
            MeasurementFunction.VOLTAGE: MeasurementCommand(
                function=MeasurementFunction.VOLTAGE,
                prepare_commands=("SYSTem:REMote", "CONFigure:VOLTage:DC"),
                query_command="MEAS1?",
                unit="V",
            ),
            MeasurementFunction.CURRENT: MeasurementCommand(
                function=MeasurementFunction.CURRENT,
                prepare_commands=("SYSTem:REMote", "CONFigure:CURRent:DC"),
                query_command="MEAS1?",
                unit="A",
            ),
        },
    ),
    InstrumentType.OWON_SPE6103: InstrumentProfile(
        instrument=InstrumentType.OWON_SPE6103,
        idn_query="*IDN?",
        idn_expected_tokens=("OWON", "SPE6103"),
        commands={
            MeasurementFunction.VOLTAGE: MeasurementCommand(
                function=MeasurementFunction.VOLTAGE,
                prepare_commands=("SYSTem:REMote",),
                query_command="MEASure:VOLTage?",
                unit="V",
            ),
            MeasurementFunction.CURRENT: MeasurementCommand(
                function=MeasurementFunction.CURRENT,
                prepare_commands=("SYSTem:REMote",),
                query_command="MEASure:CURRent?",
                unit="A",
            ),
        },
    ),
}


def idn_matches_profile(profile: InstrumentProfile, idn: str) -> bool:
    normalized = (idn or "").upper()
    return any(token in normalized for token in profile.idn_expected_tokens)
