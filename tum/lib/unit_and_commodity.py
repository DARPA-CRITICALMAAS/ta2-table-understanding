from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import orjson
import serde.json
from minmodkg.entity_linking import EntityLinking
from sm.misc.funcs import assert_not_null
from symspellpy import SymSpell
from tum.config import CRITICAL_MAAS_DIR
from tum.namespace import MNDR_NS, MNO_NS


@dataclass
class UnitAndCommodityLinkingResult:
    value: str
    unit_observed_value: Optional[str] = None
    commodity_observed_value: Optional[str] = None
    material_form_observed_value: Optional[str] = None
    unit: Optional[str] = None
    commodity: Optional[str] = None
    material_form: Optional[str] = None
    unit_score: float = 0.0
    commodity_score: float = 0.0
    material_form_score: float = 0.0

    def explain(self, linker: UnitAndCommodityLinker):
        print(f"Link {self.value} to:")
        if self.unit is not None:
            print(
                f"  - unit: {self.unit_observed_value} - {self.unit[len(MNDR_NS):]} | score = {self.unit_score:.3f} | labels = {', '.join(linker.unit_linker.id2doc[self.unit].labels)}"
            )
        else:
            print("  - unit: None")

        if self.commodity is not None:
            print(
                f"  - commodity: {self.commodity_observed_value} - {self.commodity[len(MNDR_NS):]} | score = {self.commodity_score:.3f} | labels = {', '.join(linker.commodity_linker.id2doc[self.commodity].labels)}"
            )
        else:
            print("  - commodity: None")

        if self.material_form is not None:
            print(
                f"  - material_form: {self.material_form_observed_value} - {self.material_form[len(MNDR_NS):]} | score = {self.material_form_score:.3f} | labels = {', '.join(linker.material_form_linker.id2doc[self.material_form].labels)}"
            )
        else:
            print("  - material_form: None")

    def to_dict(self, linker: Optional[UnitAndCommodityLinker] = None):
        obj = {
            "value": self.value,
            "unit_observed_value": self.unit_observed_value,
            "commodity_observed_value": self.commodity_observed_value,
            "material_form_observed_value": self.material_form_observed_value,
            "unit": self.unit,
            "commodity": self.commodity,
            "material_form": self.material_form,
            "unit_score": self.unit_score,
            "commodity_score": self.commodity_score,
            "material_form_score": self.material_form_score,
        }

        if linker is not None:
            obj.update(
                {
                    "unit_text": (
                        f"{self.unit_observed_value} - {self.unit[len(MNDR_NS):]} | score = {self.unit_score:.3f} | labels = {', '.join(linker.unit_linker.id2doc[self.unit].labels)}"
                        if self.unit is not None
                        else ""
                    ),
                    "commodity_text": (
                        f"{self.commodity_observed_value} - {self.commodity[len(MNDR_NS):]} | score = {self.commodity_score:.3f} | labels = {', '.join(linker.commodity_linker.id2doc[self.commodity].labels)}"
                        if self.commodity is not None
                        else ""
                    ),
                    "material_form_text": (
                        f"{self.material_form_observed_value} - {self.material_form[len(MNDR_NS):]} | score = {self.material_form_score:.3f} | labels = {', '.join(linker.material_form_linker.id2doc[self.material_form].labels)}"
                        if self.material_form is not None
                        else ""
                    ),
                }
            )
        return obj


class UnitAndCommodityLinker:

    instance = None

    def __init__(self, entity_dir: Path | str):
        self.entity_dir = Path(entity_dir)
        self.unit_linker = EntityLinking.get_instance(entity_dir, "unit")
        self.commodity_linker = EntityLinking.get_instance(entity_dir, "commodity")
        self.material_form_linker = EntityLinking.get_instance(
            entity_dir, "material_form"
        )

        self.linkers = {
            "unit": self.unit_linker,
            "commodity": self.commodity_linker,
            "material_form": self.material_form_linker,
        }

        # create dictionary
        self.symspell = SymSpell(max_dictionary_edit_distance=0, prefix_length=7)
        for linker in self.linkers.values():
            for doc in linker.docs:
                for label in doc.labels:
                    if label == "":
                        continue
                    self.symspell.create_dictionary_entry(label, 2)

    @staticmethod
    def get_instance(entity_dir: Path | str):
        if UnitAndCommodityLinker.instance is None:
            UnitAndCommodityLinker.instance = UnitAndCommodityLinker(entity_dir)

        assert UnitAndCommodityLinker.instance.entity_dir == Path(entity_dir)
        return UnitAndCommodityLinker.instance

    def link(self, text: str) -> UnitAndCommodityLinkingResult:
        origin_text = text
        if text.find(" ") == -1:
            # heuristics to split cases like "%Pb" to "% Pb"
            # symspell fails to correct %Pb, this is weird
            if text.startswith("%"):
                text = text[0] + " " + text[1:]
            elif text.endswith("%"):
                text = text[:-1] + " " + text[-1]
            # text = self.symspell.word_segmentation(text).corrected_string

        tokens = text.split(" ")
        out = UnitAndCommodityLinkingResult(origin_text)

        for token in tokens:
            lname, (doc, score) = max(
                [
                    (lname, assert_not_null(linker.link(token)))
                    for lname, linker in self.linkers.items()
                ],
                key=lambda x: x[1][1],
            )
            if lname == "unit":
                out.unit_observed_value = token
                out.unit = doc.id
                out.unit_score = score
            elif lname == "commodity":
                out.commodity_observed_value = token
                out.commodity = doc.id
                out.commodity_score = score
            elif lname == "material_form":
                out.material_form_observed_value = token
                out.material_form = doc.id
                out.material_form_score = score

        if out.material_form is not None and out.commodity is None:
            out.commodity = self.material_form_linker.id2doc[out.material_form].props[
                f"{MNO_NS}commodity"
            ]
            out.commodity_score = out.material_form_score

        return out


class UnitAndCommodityTrustedLinker(UnitAndCommodityLinker):
    instance = None

    def __init__(self, entity_dir: Path | str, trust_file: Path | str):
        super().__init__(entity_dir)
        self.trust_file = Path(trust_file)
        self.text2linking_result = self.load_trust_file()

    @staticmethod
    def get_instance(entity_dir: Path | str, trust_file: Path | str):
        if UnitAndCommodityTrustedLinker.instance is None:
            UnitAndCommodityTrustedLinker.instance = UnitAndCommodityTrustedLinker(
                entity_dir, trust_file
            )

        assert UnitAndCommodityTrustedLinker.instance.entity_dir == Path(entity_dir)
        assert UnitAndCommodityTrustedLinker.instance.trust_file == Path(trust_file)
        return UnitAndCommodityTrustedLinker.instance

    def link(
        self, text: str, must_be_in_trusted: bool = True, save_link: bool = False
    ) -> UnitAndCommodityLinkingResult:
        if text in self.text2linking_result:
            return self.text2linking_result[text]
        if must_be_in_trusted:
            raise ValueError(f"{text} is not in trusted linking results")
        res = super().link(text)
        if save_link:
            self.text2linking_result[text] = res
            self.save_trust_file()
        return res

    def load_trust_file(self):
        if not self.trust_file.exists():
            return {}
        linked_results = serde.json.deser(self.trust_file)
        return {
            result["value"]: UnitAndCommodityLinkingResult(
                value=result["value"],
                unit_observed_value=result["unit_observed_value"],
                commodity_observed_value=result["commodity_observed_value"],
                material_form_observed_value=result["material_form_observed_value"],
                unit=result["unit"],
                commodity=result["commodity"],
                material_form=result["material_form"],
                unit_score=result["unit_score"],
                commodity_score=result["commodity_score"],
                material_form_score=result["material_form_score"],
            )
            for result in linked_results
        }

    def save_trust_file(self):
        serde.json.ser(
            [res.to_dict(self) for res in self.text2linking_result.values()],
            self.trust_file,
            indent=2,
        )


if __name__ == "__main__":
    linker = UnitAndCommodityTrustedLinker.get_instance(
        CRITICAL_MAAS_DIR / "kgdata/data/predefined-entities",
        CRITICAL_MAAS_DIR / "sources/units_and_commodities.json",
    )

    save_link = True
    # save_link = False
    examples = [
        "%Pb",
        "%Zn",
        "g/t Ag",
        "%Cu",
        "g/t Au",
        "%Ba",
        "%Ni",
        "%Co",
        "%Sn",
        "g/t In",
        "%Mo",
        "%Fe",
        "%WO3",
        "%U3O8",
        "%As",
        "%V",
    ]
    for ex in examples:
        linker.link(ex, must_be_in_trusted=False, save_link=save_link).explain(linker)
