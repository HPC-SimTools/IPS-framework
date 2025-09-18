import tempfile

from ipsframework.ipsutil import ensemble_instances_to_csv, group_ensemble_variables_into_instances


def test_instances_to_csv():
    with tempfile.NamedTemporaryFile() as tmp:
        variables = {
            'a_comp': {'A': [3, 2, 4], 'B': [2.34, 5.82, 0.1], 'C': ['"the quick, brown fox"', 'baz', 'quux']},
            'another_comp': {'D': [7, 5, 9], 'B': [0.775, 0.08, 29.2], 'F': ['xyzzy', 'plud', 'thud']},
        }
        instances = group_ensemble_variables_into_instances(variables, 'this_is_my_name')
        expected_result = b'''\
ensemble_name,a_comp:A,a_comp:B,a_comp:C,another_comp:D,another_comp:B,another_comp:F\r
this_is_my_name0,3,2.34,"""the quick, brown fox""",7,0.775,xyzzy\r
this_is_my_name1,2,5.82,baz,5,0.08,plud\r
this_is_my_name2,4,0.1,quux,9,29.2,thud\r
'''
        ensemble_instances_to_csv(instances, tmp.name)
        actual_result = tmp.read()
        assert expected_result == actual_result
