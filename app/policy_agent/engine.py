"""Only bridge to the existing app; adapters consume snapshots, never raw CSV."""
from copy import deepcopy
from statistics import median

METRICS = {
    "youth_population": "youth_18_35_count", "job_count": "job_postings",
    "hiring_count": "hiring_count", "jobs_per_1000_youth": "youth_job_opportunity_per_1000",
    "salary": "median_salary", "rent": "rent_median",
}
UNAVAILABLE = ["opportunity_index", "job_diversity", "employment_stability"]


class QingjuEngine:
    def snapshot(self):
        from assistant_service import load_context
        return deepcopy(load_context())

    def lookup(self, district, context):
        from assistant_service import answer_question
        return answer_question(f"{district}青年人口是多少", context)

    def compare(self, districts, context):
        from assistant_service import answer_question
        return answer_question("比較" + "與".join(districts), context)


def ordered_rows(rows, metric, order, limit):
    """Thin raw-value ordering, not a composite score or policy priority.

    Nulls excluded; ties share competition rank; district name breaks display
    ties. Limit caps rows (ties may be truncated). Never modify engine values.
    """
    field = METRICS[metric]
    available = [r for r in rows if r[field] is not None]
    available.sort(key=lambda r: r["district"])
    available.sort(key=lambda r: r[field], reverse=order == "descending")
    ranked, previous, rank = [], object(), 0
    for i, row in enumerate(available, 1):
        if row[field] != previous:
            rank = i
        previous = row[field]
        ranked.append({"district": row["district"], "value": row[field], "rank": rank})
    return ranked[:limit]


def configured_observation(context, configuration):
    """Explicit M3 conjunction of the existing Policy Lens median predicates.

    Same eligible cohort as Policy Lens (available rent/ratio); not a change
    to the existing matrix, which has no high-youth/low-work conjunction.
    """
    cohort = [r for r in context["districts"] if r["youth_job_opportunity_per_1000"] is not None]
    if not cohort:
        return [], {}
    thresholds = {c["metric"]: median(r[METRICS[c["metric"]]] for r in cohort)
                  for c in configuration["conditions"]}
    def matches(row):
        return all((row[METRICS[c["metric"]]] >= thresholds[c["metric"]]
                    if c["operator"] == "high" else
                    row[METRICS[c["metric"]]] < thresholds[c["metric"]])
                   for c in configuration["conditions"])
    return [r for r in cohort if matches(r)], thresholds
