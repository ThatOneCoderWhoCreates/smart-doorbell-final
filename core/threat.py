# core/threat.py — reads from unified Config

from dataclasses import dataclass
from config import Config


@dataclass
class ThreatResult:
    score: int
    level: int
    triggered_rules: list
    recommended_action: str
    reasoning_summary: str


class ThreatScoreEngine:

    def calculate(self, face_status, dwell_time, is_nighttime,
                  audio_status, camera_status, weapon_detected):

        score = 0
        triggered_rules = []

        # Weapon contribution
        if weapon_detected:
            score += Config.WEAPON_BASE_SCORE
            triggered_rules.append(f"Weapon detected → +{Config.WEAPON_BASE_SCORE}")
            if is_nighttime:
                score += 2
                triggered_rules.append("Weapon + Night bonus +2")
            if face_status == "COVERED":
                score += 2
                triggered_rules.append("Weapon + Covered face bonus +2")

        # Face scoring
        face_score = Config.FACE_SCORES.get(face_status, 0)
        score += face_score
        triggered_rules.append(f"Face status ({face_status}) → +{face_score}")

        # Dwell time
        if dwell_time > Config.DWELL_SCORE_THRESHOLD:
            score += Config.DWELL_SCORE_POINTS
            triggered_rules.append(f"Dwell > {Config.DWELL_SCORE_THRESHOLD}s → +{Config.DWELL_SCORE_POINTS}")

        if face_status == "UNKNOWN" and dwell_time > Config.UNKNOWN_LONG_DWELL_SECONDS:
            score += Config.UNKNOWN_LONG_DWELL_BONUS
            triggered_rules.append("Unknown + >60s dwell → +2 bonus")

        # Nighttime
        if is_nighttime:
            score += Config.NIGHT_SCORE
            triggered_rules.append("Night time → +2")
        if face_status == "COVERED" and is_nighttime:
            score += Config.COVERED_NIGHT_BONUS
            triggered_rules.append("Covered + Night combo → +3 bonus")

        # Audio
        audio_score = Config.AUDIO_SCORES.get(audio_status, 0)
        score += audio_score
        if audio_score > 0:
            triggered_rules.append(f"Audio ({audio_status}) → +{audio_score}")

        # Camera obstruction
        if camera_status == "OBSTRUCTED":
            score += Config.CAMERA_OBSTRUCTION_SCORE
            triggered_rules.append("Camera obstructed → +5")

        # Level
        level = self._determine_level(score)
        if weapon_detected:
            level = max(level, Config.WEAPON_MIN_LEVEL)

        return self._build_result(score, level, triggered_rules)

    def _determine_level(self, score):
        if score <= Config.NORMAL_MAX_SCORE:
            return 0
        elif score <= Config.SUSPICIOUS_MAX_SCORE:
            return 1
        return 2

    def _build_result(self, score, level, triggered_rules):
        level_name = Config.THREAT_LEVELS[level]
        actions = {
            0: "Log event only",
            1: "Record short clip + send alert",
            2: "Trigger alarm + continuous recording + emergency alert",
        }
        return ThreatResult(
            score=score,
            level=level,
            triggered_rules=triggered_rules,
            recommended_action=actions[level],
            reasoning_summary=f"Threat Level: {level_name} | Score: {score}",
        )
