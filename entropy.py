from collections import defaultdict
import math

def calc_entropy(data, target_attr):
    """
    Calculates the entropy of the given data set for the target attribute.
    """
    val_freq     = {}
    data_entropy = 0.0

    # filter out ties
    data = [r for r in data if r[target_attr] != 0.5]
    for record in data:
        if (val_freq.has_key(record[target_attr])):
            val_freq[record[target_attr]] += 1.0
        else:
            val_freq[record[target_attr]]  = 1.0

    print_freq = {}
    for val in val_freq:
        if val == 0:
            term = 'lost'
        elif val == 0.5:
            term = 'tied'
        else:
            term = 'won'
        print_freq[term] = val_freq[val]

    # Calculate the entropy of the data for the target attribute
    for freq in val_freq.values():
        data_entropy += (-freq/len(data)) * math.log(freq/len(data), 2)

    return data_entropy, print_freq


def make_readable(data, segment_value, target):
    """
    Print the number of records in the input data make_readabled into win/loss.
    """
    SEGMENT_TO_ENGLISH = {
        0: 'lost',
        0.5: 'tied',
        1: 'won'
    }
    wins = len([r for r in data if r[target]])
    losses = len([r for r in data if not r[target]])
    return SEGMENT_TO_ENGLISH[segment_value], {'wins': wins, 'losses': losses}


def gain(data, segment_attr, target_attr):
    """
    Calculates the information gain (reduction in entropy) that would
    result by splitting the data on the chosen attribute (attr).

    :param list data: A list of dictionaries mapping attributes to values.
    :param str attr: The attribute to segment by.
    :param str target_attr: The attribute to predict.
    """
    outcome_frequency = defaultdict(int)
    # filter out ties
    data = [r for r in data if r[segment_attr] != 0.5]
    for record in data:
        outcome = record[segment_attr]
        outcome_frequency[outcome] += 1.0

    entropy_of_segments = 0.0
    for outcome, frequency in outcome_frequency.iteritems():
        proportion = round(frequency / len(data), 4)

        # find the values for target_attr (i.e. 'win') in the original dataset where the value of segment_attr ('3pt')
        # match this particular outcome (i.e. 1)
        matched_subset = [{target_attr: r[target_attr]} for r in data if r[segment_attr] == outcome]
        verb, win_loss = make_readable(matched_subset, outcome, target_attr)
        entropy = round(calc_entropy(matched_subset, target_attr)[0], 4)
        entropy_of_segments += proportion * entropy
        # print '{1} {0}, {2}, proportion: {3}, entropy: {4}'.format(verb, segment_attr, win_loss, proportion, entropy)

    parent_entropy = round(calc_entropy(data, target_attr)[0], 4)
    gain = round(parent_entropy - entropy_of_segments, 4)
    # print 'parent entropy: {0}, total segment entry: {1}, gain: {2}'.format(parent_entropy, entropy_of_segments, gain)
    return gain
