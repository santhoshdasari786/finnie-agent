from src.rag.common.registry import register

@register("postprocessor", "threshold")
class ThresholdFilter:
    def __init__(self, min_score):
        self.min_score = min_score

    def process(self, query, hits):
        return [h for h in hits if h.score >= self.min_score]
