import pytest
from quantlab.data.core import Dataset, normalize, validate, total_return_index


@pytest.mark.parametrize(
    "mutation,fragment",
    [
        (lambda f: f.iloc[1:], "missing sessions"),
        (lambda f: __import__("pandas").concat([f, f.iloc[:1]]), "Duplicate"),
        (lambda f: f.assign(volume=-1), "Negative"),
        (lambda f: f.assign(open=0), "Nonpositive"),
        (lambda f: f.assign(high=1), "OHLC"),
        (lambda f: f.assign(symbol=None), "Missing"),
        (lambda f: f.assign(split=0), "split"),
        (lambda f: f.assign(dividend=1, split=2), "Simultaneous"),
    ],
)
def test_invalid_data(small_data, mutation, fragment):
    with pytest.raises(ValueError, match=fragment):
        Dataset.create(mutation(small_data.frame), {})


def test_timezone_and_intraday_rejected(small_data):
    import pandas as pd

    for dates in [
        small_data.frame.date.dt.tz_localize("UTC"),
        small_data.frame.date + pd.Timedelta(hours=1),
    ]:
        with pytest.raises(ValueError, match="midnight"):
            normalize(small_data.frame.assign(date=dates))


def test_split_causal_index(small_data):
    f = small_data.frame.copy()
    first = f.date.unique()[3]
    f.loc[(f.symbol == "A") & (f.date >= first), ["open", "high", "low", "close"]] /= 2
    f.loc[(f.symbol == "A") & (f.date == first), "split"] = 2
    index = total_return_index(Dataset.create(f, {}).frame)
    assert index.A.eq(1).all()
    assert total_return_index(f[f.date < first]).equals(index[index.index < first])


def test_dividend_return(small_data):
    f = small_data.frame.copy()
    date = f.date.unique()[1]
    f.loc[(f.symbol == "A") & (f.date >= date), ["open", "high", "low", "close"]] = 9
    f.loc[(f.symbol == "A") & (f.date == date), "dividend"] = 1
    assert total_return_index(f).A.eq(1).all()


def test_warning_and_fingerprint(small_data, tmp_path):
    assert validate(small_data.frame)["warnings"]
    path = small_data.save(tmp_path)
    assert Dataset.load(path).fingerprint == small_data.fingerprint
    f = small_data.frame.copy()
    f.loc[0, "volume"] += 1
    f.to_parquet(path / "bars.parquet", index=False)
    with pytest.raises(ValueError, match="fingerprint"):
        Dataset.load(path)


def test_calendar_holiday_bounds():
    from quantlab.data.core import sessions

    assert str(sessions("2018-01-01", "2018-01-07")[0].date()) == "2018-01-02"
    assert len(sessions("2020-01-02", "2020-01-02")) == 1
