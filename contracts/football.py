# { "Depends": "py-genlayer:test" }
from genlayer import *
import json

class GenPredict(gl.Contract):
    matches: TreeMap[str, str]
    user_stakes: TreeMap[str, str]
    match_count: u256

    def __init__(self):
        self.match_count = u256(0)

    @gl.public.write
    def create_match(self, match_id: str, home_team: str, away_team: str, league: str, match_date: str) -> None:
        match = {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "match_date": match_date,
            "home_stakes": 0,
            "draw_stakes": 0,
            "away_stakes": 0,
            "resolved": False,
            "result": ""
        }
        self.matches[match_id] = json.dumps(match)
        self.match_count += u256(1)

    @gl.public.write
    def stake(self, match_id: str, prediction: str, amount: int, user_address: str) -> None:
        if match_id not in self.matches:
            raise Exception("Match not found")
        match = json.loads(self.matches[match_id])
        if match["resolved"]:
            raise Exception("Match already resolved")
        if prediction not in ["home", "draw", "away"]:
            raise Exception("Invalid prediction")

        stake_key = match_id + "_" + user_address
        stake = {"amount": amount, "prediction": prediction, "claimed": False}
        self.user_stakes[stake_key] = json.dumps(stake)

        match[prediction + "_stakes"] += amount
        self.matches[match_id] = json.dumps(match)

    @gl.public.write
    def resolve_match(self, match_id: str) -> None:
        if match_id not in self.matches:
            raise Exception("Match not found")
        match = json.loads(self.matches[match_id])
        if match["resolved"]:
            raise Exception("Already resolved")

        def check_result():
            prompt = f"""
            What was the result of the football match between {match['home_team']} and {match['away_team']} on {match['match_date']}?
            Did the home team win, was it a draw, or did the away team win?
            Respond ONLY with JSON: {{"result": "home"}} or {{"result": "draw"}} or {{"result": "away"}}
            """
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps({"result": res["result"]})

        principle = "Both answers must agree on the match result: home win, draw or away win"
        output = gl.eq_principle.prompt_comparative(check_result, principle)
        parsed = json.loads(output)

        match["resolved"] = True
        match["result"] = parsed["result"]
        self.matches[match_id] = json.dumps(match)

    @gl.public.view
    def get_match(self, match_id: str) -> str:
        if match_id not in self.matches:
            return "{}"
        return self.matches[match_id]

    @gl.public.view
    def get_user_stake(self, match_id: str, user: str) -> str:
        stake_key = match_id + "_" + user
        if stake_key not in self.user_stakes:
            return "{}"
        return self.user_stakes[stake_key]

    @gl.public.view
    def get_match_count(self) -> int:
        return int(self.match_count)