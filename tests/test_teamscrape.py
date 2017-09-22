from scraper.teamscrape import scrape_game_data
from scraper.teamscrape_refactored import BoxScore, winners_for_stat
import unittest


class TestTeamScrape(unittest.TestCase):

    def test_scrape_data(self):
        game_url = 'https://www.basketball-reference.com/boxscores/201610250CLE.html'
        raw_game_data = scrape_game_data(game_url)
        box_score_data = BoxScore(game_url).parse(winners_for_stat)
        self.assertEqual(box_score_data, raw_game_data)

