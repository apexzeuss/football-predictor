# { "Depends": "py-genlayer:test" }
from genlayer import *
import json

class FootballPredictor(gl.Contract):
    predictions: dict
    scores: dict

    def __init__(self):
        self.predictions = {}
        self.scores = {}

    @gl.public.write
    def create_prediction(self, match_id: str, home_team: str, away_team: str, match_date: str) -> None:
        self.predictions[match_id] = {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": match_date,
            "yes_votes": 0,
            "no_votes": 0,
            "resolved": False,
            "result": None
        }

    @gl.public.write
    def vote(self, match_id: str, vote_yes: bool) -> None:
        if match_id not in self.predictions:
            raise Exception("Match not found")
        if self.predictions[match_id]["resolved"]:
            raise Exception("Match already resolved")
        if vote_yes:
            self.predictions[match_id]["yes_votes"] += 1
        else:
            self.predictions[match_id]["no_votes"] += 1

    @gl.public.write
    def resolve(self, match_id: str, api_key: str) -> None:
        if match_id not in self.predictions:
            raise Exception("Match not found")
        
        match = self.predictions[match_id]
        home_team = match["home_team"]
        away_team = match["away_team"]

        def check_result():
            url = f"https://v3.football.api-sports.io/fixtures?date={match['match_date']}&timezone=UTC"
            web_data = gl.nondet.web.get(url, mode="text", extra_headers={"x-apisports-key": api_key})
            
            prompt = f"""
            Based on this football API data: {web_data}
            Did {home_team} win against {away_team}?
            Respond ONLY with JSON: {{"home_win": true}} or {{"home_win": false}}
            """
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps(res, sort_keys=True)

        output = gl.eq_principle.strict_eq(check_result)
        parsed = json.loads(output)
        
        self.predictions[match_id]["resolved"] = True
        self.predictions[match_id]["result"] = parsed["home_win"]

    @gl.public.view
    def get_prediction(self, match_id: str) -> str:
        if match_id not in self.predictions:
            return "{}"
        return json.dumps(self.predictions[match_id])

    @gl.public.view
    def get_all_predictions(self) -> str:
        return json.dumps(self.predictions)