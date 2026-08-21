from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceManifest:
    repository: str
    tag: str
    commit: str
    filename: str
    download_url: str
    sha256: str
    size_bytes: int
    license_name: str
    license_url: str


ECDICT_SOURCE = SourceManifest(
    repository="https://github.com/skywind3000/ECDICT",
    tag="1.0.28",
    commit="8defb761f7c7ad1818ca94290a1844d7b33d6b23",
    filename="ecdict.csv",
    download_url=(
        "https://raw.githubusercontent.com/skywind3000/ECDICT/"
        "8defb761f7c7ad1818ca94290a1844d7b33d6b23/ecdict.csv"
    ),
    sha256="d0ce61e560b50d9905d20de3173aa3ca80950ce235bedd21c53e025cf9f38cb0",
    size_bytes=65_936_699,
    license_name="MIT",
    license_url=(
        "https://github.com/skywind3000/ECDICT/blob/"
        "8defb761f7c7ad1818ca94290a1844d7b33d6b23/LICENSE"
    ),
)
