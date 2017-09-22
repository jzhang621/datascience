from collections import defaultdict

from bs4 import BeautifulSoup
from requests import get

from config import ALL_TEAMS, IGNORED_STATS, USED_STATS
from utils import cached

BASE_URL = 'http://www.basketball-reference.com'


@cached(3600 * 24 * 7)
def _get_html(url):
    """
    Request the data for this game_url in its raw html form.
    Convert it into a BeautifulSoup object for parsing.

    Note: this is a stand-alone function in order to work with the caching decorator.
    """
    raw_html = get(url).text
    return BeautifulSoup(raw_html, 'html.parser')


@cached(3600 * 24 * 7)
def get_reg_season_games(url):
    """
    Return a list of scrapable links.
    """
    raw_html = get(url).text
    parser = BeautifulSoup(raw_html, 'html.parser')

    game_links = []
    links = parser.find('div', {'id': 'all_games'}).findAll('td', {'data-stat': 'box_score_text'})
    for link in links:
        url = link.find('a')
        if url.text:
            game_links.append(BASE_URL + url['href'])

    assert len(game_links) == 82
    return game_links


def parse_team_name(table_html):
    """
    Given a box score table in html form, return the team name for which that table applies to.
    """
    return table_html['id'].split('_')[1]


def winners_for_stat(team_to_stats):
    """
    Given raw team to stat data, consolidate the input by winners of each stat.
    """
    def _calc(stat, direction):
        """
        For the given stat and direction, return a dictionary of team name to
        a boolean indicating if the team "won" the stat.
        """
        t1_stat = team_to_stats[t1][stat]
        t2_stat = team_to_stats[t2][stat]

        if t1_stat == t2_stat:
            return {t1: 0.5, t2: 0.5}

        if direction == MORE:
            if t1_stat > t2_stat:
                return {t1: 1, t2: 0}
            else:
                return {t1: 0, t2: 1}
        else:
            if t1_stat < t2_stat:
                return {t1: 1, t2: 0}
            else:
                return {t1: 0, t2: 1}

    t1, t2 = teams[0], teams[1]

    MORE = 1
    LESS = 0

    teams = team_to_stats.keys()

    t1_results, t2_results = {}, {}
    for stat in USED_STATS:
        direction = LESS if stat in {'tov', 'tov_pct'} else MORE
        result = _calc(stat, direction)
        if stat == 'pts':
            stat = 'win'

        t1_results.update({stat: result[t1]})
        t2_results.update({stat: result[t2]})

    return {t1: t1_results, t2: t2_results}


class BoxScore(object):
    """
    Class which encapsulates a single basketball-reference box score. Contains methods for parsing data from this box score.
    """
    def __init__(self, game_url):
        self.game_url = game_url

    def _parse_html(self):
        """
        Scrape the contents of this box score into a dictionary mapping
        team name to raw stats.

        e.g.:
        {
         'nyk': {'fg3a_per_fga_pct': 0.31, 'orb_pct': 24.5, ... },
         'cle': {'fg3a_per_fga_pct': 0.372, 'orb_pct': 27.5, ... }
        }
        """
        html = _get_html(self.game_url)

        team_to_stats = defaultdict(dict)
        for table in html.findAll('table', {'class': 'stats_table'}):
            team = parse_team_name(table)
            totals_row = table.find('tfoot')
            for column in totals_row.findAll('td'):
                category = column['data-stat']
                if category not in IGNORED_STATS:
                    team_to_stats[team][category] = float(column.text)

        return team_to_stats

    def apply_func(self, aggregate_func):
        """
        Apply the function which takes the parse html into usuable output.
        """
        return aggregate_func(self._parse_html())


class TeamScraper(object):

    TEAM_URL = 'http://www.basketball-reference.com/teams/{0}/2017_games.html'

    def __init__(self, team_name):
        self.team_name = team_name

    def get_per_game_data(self, func):
        """
        Scrape all regular season games for the given team, and apply the given aggregation function to each result.

        :param function func: An aggregation function to apply to raw per-game data.
        :return: A list of data elements, one for each regular season game.
        """
        url = self.TEAM_URL.format(self.team_name.upper())

        results = []
        for game_link in get_reg_season_games(url):
            box_score = BoxScore(game_link)
            results.append(box_score.parse(func)[self.team_name])

        return results

    def calc_stat_importance(self):
        """
        Calculate the "importance" of each statistic based on per-game data.
        The importance of a stat is defined here as the team's win % when a given stat is won.

        :return: Dictionary mapping stats to their importance.
        """
        data = self.get_per_game_data()

        wins = float(len([_ for _ in data if _['win'] == 1]))
        base_win_pct = round(wins / len(data), 3)

        diffs = {'base_win_pct': base_win_pct}
        for stat in data[0].keys():
            stat_wins = [_ for _ in data if _[stat] == 1]
            wins_with_stat_win = float(len([_ for _ in stat_wins if _['win'] == 1]))
            win_pct = wins_with_stat_win / len(stat_wins)

            stat = stat.replace('_pct', '%')

            # this is where I can change importance
            diffs[stat] = {'pct_diff': round(win_pct, 3), 'total': len(stat_wins)}

        return {'team_name': self.team_name, 'diffs': diffs}


if __name__ == '__main__':

    all_data = []
    for team in ALL_TEAMS:
        stat_importance = TeamScraper(team).calc_stat_importance()
        print team_diffs
        all_data.append(team_diffs)

    import json
    with open('team_diff_data.json', 'w') as diff_data_file:
        json.dump(all_data, diff_data_file)
