#################################################################################
# PRIMO - The P&A Project Optimizer was produced under the Methane Emissions
# Reduction Program (MERP) and National Energy Technology Laboratory's (NETL)
# National Emissions Reduction Initiative (NEMRI).
#
# NOTICE. This Software was developed under funding from the U.S. Government
# and the U.S. Government consequently retains certain rights. As such, the
# U.S. Government has been granted for itself and others acting on its behalf
# a paid-up, nonexclusive, irrevocable, worldwide license in the Software to
# reproduce, distribute copies to the public, prepare derivative works, and
# perform publicly and display publicly, and to permit others to do so.
#################################################################################

# Standard libs
import os

# Installed libs
import playwright
import pytest

# User-defined libs
from primo.utils.config_utils import (
    SelectWidget,
    _get_checkbox_params,
    copy_dict,
    copy_values,
    is_valid,
    read_config,
    read_defaults,
    update_defaults,
)


@pytest.mark.parametrize(
    "input_dict,output_dict,result,status_ok",
    [
        # Existing test cases
        (
            {
                "input_str": "orange",
                "input_float": 42.0,
                "input_dict": {"nested_str": "banana", "nested_int": 42},
            },
            {
                "input_str": "apple",
                "input_float": 99.0,
                "input_dict": {"nested_str": "banana", "nested_int": 83},
                "input_default": "default",
            },
            {
                "input_str": "orange",
                "input_float": 42.0,
                "input_dict": {"nested_str": "banana", "nested_int": 42},
                "input_default": "default",
            },
            True,
        ),
        ({}, {}, {}, True),
        (
            {"unknown_input": 33, "known_input": "OK"},
            {"known_input": "AOK"},
            {},
            False,
        ),
        # New test cases
        (
            {"input_list": [1, 2, 3]},
            {"input_list": [4, 5, 6]},
            {"input_list": [1, 2, 3]},
            True,
        ),
        (
            {"input_str": "orange", "input_float": 42.0, "extra_key": "unexpected"},
            {"input_str": "apple", "input_float": 99.0},
            {},
            False,
        ),
    ],
)
def test_copy_dict(input_dict, output_dict, result, status_ok):
    if status_ok:
        assert copy_dict(input_dict, output_dict) == result
    else:
        with pytest.raises(ValueError):
            copy_dict(input_dict, output_dict)


@pytest.mark.parametrize(
    "input_dict,reference_dict,result",
    [
        # Existing test cases
        (
            {
                "input_str": "orange",
                "input_float": 42.0,
                "input_dict": {"nested_str": "banana", "nested_int": 42},
            },
            {
                "input_str": "apple",
                "input_float": 99.0,
                "input_dict": {"nested_str": "banana", "nested_int": 83},
                "input_default": "default",
            },
            True,
        ),
        ({}, {}, True),
        (
            {"unknown_input": 33, "known_input": "OK"},
            {"known_input": "AOK"},
            False,
        ),
        (
            {"input_str": "orange", "input_float": 42.0},
            {
                "input_str": "orange",
                "input_float": 42.0,
                "input_dict": {"nested_str": "banana", "nested_int": 42},
            },
            True,
        ),
        (
            {"input_str": "orange", "input_float": 42.0},
            {
                "input_string": "orange",
                "input_float": 42.0,
                "input_dict": {"nested_str": "banana", "nested_int": 42},
            },
            False,
        ),
        # New test cases
        (
            {"input_list": [1, 2, 3]},
            {"input_list": [4, 5, 6]},
            True,
        ),
        (
            {"input_str": "orange", "input_float": 42.0, "extra_key": "unexpected"},
            {"input_str": "apple", "input_float": 99.0},
            False,
        ),
    ],
)
def test_is_valid(input_dict, reference_dict, result):
    assert is_valid(input_dict, reference_dict) == result


@pytest.mark.parametrize(
    "path,expected_result",
    [
        ("valid_config.json", (True, {"key": "value"})),
        ("invalid_config.json", (False, {})),
    ],
)
def test_read_config(monkeypatch, path, expected_result):
    def mock_exists(p):
        return p == "valid_config.json"

    def mock_open(p, mode):
        class MockFile:
            def read(self):
                return '{"key": "value"}'

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                pass

        return MockFile()

    # Patch the os.path.exists and open functions using monkeypatch
    monkeypatch.setattr(os.path, "exists", mock_exists)
    monkeypatch.setattr("builtins.open", mock_open)

    # Assert that the function output matches the expected result
    assert read_config(path) == expected_result


@pytest.mark.parametrize(
    "config_dict,input_dict,expected_result",
    [
        (
            {"key": {"default": 10, "sub_weights": {"sub_key": {"default": 20}}}},
            {"key": {"default": 5, "sub_weights": {"sub_key": {"default": 10}}}},
            {"key": {"default": 10, "sub_weights": {"sub_key": {"default": 20}}}},
        ),
        (
            {"key": {"default": 0, "sub_weights": {"sub_key": {"default": 0}}}},
            {"key": {"default": 5, "sub_weights": {"sub_key": {"default": 10}}}},
            {"key": {"default": 0, "sub_weights": {"sub_key": {"default": 0}}}},
        ),
    ],
)
def test_update_defaults(config_dict, input_dict, expected_result):
    assert update_defaults(config_dict, input_dict) == expected_result


@pytest.mark.parametrize(
    "input_dict,expected_priority,expected_sub_priority",
    [
        (
            {"key": {"default": 10, "sub_weights": {"sub_key": {"default": 20}}}},
            {"key": 10},
            {"key": {"sub_key": 20}},
        ),
        (
            {"key": {"default": 0, "sub_weights": {"sub_key": {"default": 0}}}},
            {"key": 0},
            {},
        ),
    ],
)
def test_read_defaults(input_dict, expected_priority, expected_sub_priority):
    assert read_defaults(input_dict) == (expected_priority, expected_sub_priority)


@pytest.mark.parametrize(
    "input_dict,output_dict,key,expected_result",
    [
        (
            {"key": {"sub_key": "value"}},
            {"key": {"sub_key": "default_value"}},
            "key",
            {"key": {"sub_key": "value"}},
        ),
        (
            {"key": "value"},
            {"key": "default_value"},
            "key",
            {"key": "value"},
        ),
    ],
)
def test_copy_values(input_dict, output_dict, key, expected_result):
    assert copy_values(input_dict, output_dict, key) == expected_result


@pytest.mark.parametrize(
    "param_dict,expected_result",
    [
        (
            {"default": 5, "min_val": 0, "max_val": 100, "incr": 1},
            (5, 0, 100, 1),
        ),
        (
            {"default": 5},
            (5, 0, 100, 5),
        ),
    ],
)
def test_get_checkbox_params(param_dict, expected_result):
    assert _get_checkbox_params(param_dict) == expected_result


@pytest.mark.widgets
def test_select_widget(solara_test, page_session: playwright.sync_api.Page):
    choices = ["Apple", "Banana", "Mango"]
    button_description = "Select fruit"
    type_description = "Fruit"
    widget_class = SelectWidget(choices, button_description, type_description)
    widget_class.display()

    # Assert list is empty initially
    assert not widget_class.selected_list

    # Add Apple to form
    page_session.get_by_label("Fruit").fill("Apple")
    select_button = page_session.locator("text=Select fruit")
    select_button.click()

    assert widget_class.selected_list == ["Apple"]

    # Add Banana to form
    page_session.get_by_label("Fruit").fill("Banana")
    select_button.click()
    assert widget_class.selected_list == ["Apple", "Banana"]

    # Unselect recent selection
    undo_button = page_session.locator("text=Undo")
    undo_button.click()
    assert widget_class.selected_list == ["Apple"]

    # TODO: Add more tests
