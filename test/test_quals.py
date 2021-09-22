
from coups.quals import dashed
def test_dashes():
    for give,want in [
            ('c7:p392:prof','c7:p392:prof'),
            ('c7:debug:p392','c7:p392:debug')]:
        dqs = dashed(give)
        got = dqs.replace("-",":")
        assert got == want
