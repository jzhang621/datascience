from collections import defaultdict
import re
import operator

from entropy import calc_entropy, gain
from utils import cached, timeit
from bs4 import BeautifulSoup
from requests import get
from urllib2 import urlopen
import json
from pandas import DataFrame as df
import concurrent.futures
import time
import multiprocessing as mp


years = [i for i in range(2000, 2018)]

GAME_SCHEDULE_URL = 'http://www.basketball-reference.com/leagues/NBA_{1}_games-{0}.html'
BASE_URL = 'http://www.basketball-reference.com'
TEAM_URL = 'http://www.basketball-reference.com/teams/{0}/2017_games.html'

ALL_TEAMS = ['sac', 'por', 'sas', 'brk', 'ind', 'mil', 'min', 'mia', 'cle', 'cho', 'nyk', 'hou', 'was', 'lal', 'phi', 'pho', 'dal', 'lac', 'orl', 'nop', 'uta', 'gsw', 'atl', 'bos', 'det', 'okc', 'tor', 'den', 'chi', 'mem']

MONTHS = ['october', 'november', 'december', 'january', 'february', 'march', 'april', 'may']
IGNORED_CAT = {'mp', 'plus_minus', 'usg_pct', 'off_rtg', 'def_rtg', 'win'}

STATS = ['fg', 'fga', 'fg_pct', 'fg3', 'fg3_pct', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'ts_pct', 'efg_pct', 'fta', 'ft']

def get_raw_game_data(game_url):
    """
    In:
    :param str game_url: A box score to parse.

    Out:
    :return: Dictionary mapping team name to raw stats.
    """
    raw_html = get(game_url).text
    parser = BeautifulSoup(raw_html, 'html.parser')

    # parse raw totals for each team
    raw_team_stats = defaultdict(dict)
    for table in parser.findAll('table', {'class': 'stats_table'}):
        team = table['id'].split('_')[1]
        totals_row = table.find('tfoot')
        for column in totals_row.findAll('td'):
            category = column['data-stat']
            if category not in IGNORED_CAT:
                raw_team_stats[team][category] = float(column.text)

    return raw_team_stats


def scrape_game_data(game_url):
    """
    Scrape data from a game into a dictionary mapping stat categories to booleans
    indicating if the given team won the particular category
    """
    raw_team_stats = get_raw_game_data(game_url)

    # convert raw totals to booleans if the given team won the particular stat.
    teams = raw_team_stats.keys()
    stats = raw_team_stats.values()
    parsed_team_stats = defaultdict(dict)

    for cat in stats[0].keys():
        write_cat = 'win' if cat == 'pts' else cat

        if cat == 'tov' or cat == 'tov_pct':

            if stats[0][cat] > stats[1][cat]:
                parsed_team_stats[teams[0]][write_cat] = 0
                parsed_team_stats[teams[1]][write_cat] = 1
            elif stats[0][cat] < stats[1][cat]:
                parsed_team_stats[teams[0]][write_cat] = 1
                parsed_team_stats[teams[1]][write_cat] = 0
            else:
                parsed_team_stats[teams[0]][write_cat] = 0.5
                parsed_team_stats[teams[1]][write_cat] = 0.5

        else:
            if stats[0][cat] > stats[1][cat]:
                parsed_team_stats[teams[0]][write_cat] = 1
                parsed_team_stats[teams[1]][write_cat] = 0
            elif stats[0][cat] < stats[1][cat]:
                parsed_team_stats[teams[0]][write_cat] = 0
                parsed_team_stats[teams[1]][write_cat] = 1
            else:
                parsed_team_stats[teams[0]][write_cat] = 0.5
                parsed_team_stats[teams[1]][write_cat] = 0.5
    return parsed_team_stats





@cached(24 * 3600 * 7)
def get_team_data(team):
    """
    Return a list of results for the given team.
    """
    results = []
    for link in get_game_links(TEAM_URL.format(team.upper())):
        game_data = scrape_game_data(link)[team.lower()]
        results.append(game_data)
    return results


@cached(24 * 3600 * 7)
def get_game_links(url):
    """
    Return a list of scrape-able links.
    """
    raw_html = get(url).text
    parser = BeautifulSoup(raw_html, 'html.parser')

    game_links = []
    links = parser.findAll('td', {'data-stat': 'box_score_text'})
    for link in links:
        url = link.find('a')
        if url.text:
            game_links.append(BASE_URL + url['href'])

    return game_links


@cached(3600 * 24 * 7)
def get_all_game_links(year):
    """
    Return a list of all results for the given season.
    """
    links = []

    for month in MONTHS:
        url = GAME_SCHEDULE_URL.format(month, year)
        print 'getting games for {0}'.format(url)
        links.extend(get_game_links(url))

    return links

def get_raw_data_request(game_url):
    return get(game_url).text


@timeit
def get_all_teams_data(year):

    links = get_all_game_links(year)
    results = []
    for link in links:
        game_data = scrape_game_data(link)
        results.append(game_data)

    print results
    return results

    """
    pool = mp.Pool(processes=4)
    results = [pool.map_async(scrape_game_data, links)]
    print [r.get() for r in results]
    pool.terminate()
    pool.join()

    for link in get_all_game_links(year):
        game_data = scrape_game_data(link)
        for team, team_data in game_data.iteritems():
            team_data['team'] = team
            print team_data
            # results.append(team_data)

    # return results
    """


def calc_team_gain(team_results):

    gains = {}
    for cat in team_results[0].keys():
        g = gain(team_results, cat, 'win')
        gains[cat] = g

    return gains

def print_sorted(values, details):

    sorted_values = sorted(values.items(), key=operator.itemgetter(1), reverse=True)
    for g in sorted_values:
        print g, details[g[0]]


def to_win_probability(team_name):

    team_df = []
    team_data = get_team_data(team_name)
    total_wins = len([x for x in team_data if x['win']])
    base_pct = round(total_wins / float(len(team_data)), 2)
    team_frame = frame.loc[frame['team'] == team_name]

    for stat in team_data[0].keys():
        wins_stat = [x for x in team_data if x[stat]]
        loss_stat = [x for x in team_data if not x[stat]]

        w_when_stat_wins = len([x for x in wins_stat if x['win']])
        l_when_stat_wins = len([x for x in wins_stat if not x['win']])
        total_when_stat_wins = float(w_when_stat_wins + l_when_stat_wins)
        win_w_pct = round(w_when_stat_wins / total_when_stat_wins,  3)

        entropy_when_win = calc_entropy(wins_stat, 'win')
        entropy_when_loss = calc_entropy(loss_stat, 'win')

        w_when_stat_loss = len([x for x in loss_stat if x['win']])
        l_when_stat_loss = len([x for x in loss_stat if not x['win']])
        total_when_stat_loss = float(w_when_stat_loss + l_when_stat_loss)
        loss_w_pct = round(w_when_stat_loss / total_when_stat_loss,  3)
        gain = team_frame[stat].iloc[0]

        if stat in ['ast', 'fg']:
            print stat, gain, entropy_when_win, entropy_when_loss

        data = {
          'w_wins': w_when_stat_wins,
          'w_losses': l_when_stat_wins,
          'stat': stat,
          'base_pct': base_pct,
          'adj_pct': round(win_w_pct - base_pct, 2),
          'gain': gain,
          't_stat_w': int(total_when_stat_wins),
          't_stat_l': int(total_when_stat_loss),
          'l_wins': w_when_stat_loss,
          'l_loss': l_when_stat_loss
        }
        team_df.append(data)

    return df(team_df)


if __name__ == '__main__':

    sgd = scrape_game_data('https://www.basketball-reference.com/boxscores/201610250CLE.html')

    print sgd
    import pdb; pdb.set_trace()

    all_years = {}
    total_years = {}
    raw_totals = {}
    for year in [years[-1]]:
        data_for_year = get_all_teams_data(year)
        import pdb; pdb.set_trace()

        """
        results = df(data_for_year)
        results.to_csv('raw_game_data_{0}'.format(year))

        year_dict = {year: {}}
        total_year_dict = {year: {}}
        raw_totals_year = {year: {}}
        total_stat_wins = 0
        for stat in STATS:
            won_stat = results[results[stat] == 1]
            wins = results[results['win'] == 1]
            stat_wins = len(wins[wins[stat] ==1])
            total_stat_wins += stat_wins
            wins_when_stat_is_won = won_stat[won_stat['win'] == 1]
            win_pct = round(len(wins_when_stat_is_won) / float(len(won_stat)), 4)
            pct_of_games = 100 * round(len(won_stat) / float(len(results)), 4)

            total_year_dict[year].update({stat: stat_wins})
            year_dict[year].update({stat: win_pct})
            raw_totals_year[year].update({stat: len(wins_when_stat_is_won)})

        year_dict[year].update({'total_win_pct': float(total_stat_wins) / len(results) * len(STATS), 'total_win': total_stat_wins})
        all_years.update(year_dict)
        total_years.update(total_year_dict)
        raw_totals.update(raw_totals_year)

    frame = df.from_dict(all_years, orient='index')
    totals = df.from_dict(total_years, orient='index')
    wins_when_stat_is_won = df.from_dict(raw_totals, orient='index')
    wins_when_stat_is_won.to_csv('wins_when_stat_is_won.csv')
    import pdb; pdb.set_trace()
    """
