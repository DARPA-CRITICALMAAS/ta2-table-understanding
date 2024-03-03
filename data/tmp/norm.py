import pandas as pd
import serde.csv

lst = serde.csv.deser("data/tmp/Mudd-and-Jowitt-2022-Nickel.csv")
out = []
for x in lst[3:]:
    for i, cat in enumerate(["Measured", "Indicated", "Inferred"]):
        out.append(
            {
                "Country": x[0],
                "Project": x[1],
                "Lat": x[2],
                "Long": x[3],
                "Company": x[4],
                "Category": cat,
                "Mt": x[5 + i * 2],
                "%Ni": x[6 + i * 2],
                "Source": x[11],
                "Primary Deposit Type": x[12],
                "Secondary Deposit Type": x[13],
                "Other Deposit Type": x[14],
            }
        )


pd.DataFrame(out).to_csv("examples/tables/Mudd-and-Jowitt-2022-Nickel.csv", index=False)
