from corehq.apps.userreports.expressions.factory import ExpressionFactory
from corehq.apps.userreports.specs import TypeProperty
from dimagi.ext.jsonobject import JsonObject, DictProperty

class GetCaseFormsByDateSpec(JsonObject):
    type = TypeProperty('get_case_forms_by_date')
    case_id_expression = DefaultProperty(required=True)
    start_date = DefaultProperty()
    end_date = DefaultProperty()
    xmlns = StringProperty()
    
def get_case_forms_by_date(spec, context):
    GetCaseFormsByDateSpec.wrap(spec)  # this is just for validation
    filters = []
    if spec['start_date'] is not None:
        start_date_filter = {
            "operator": "gte",
            "expression": {
              "datatype": "integer",
              "from_date_expression": spec['start_date'],
              "type": "diff_days",
              "to_date_expression": {
                "datatype": "date",
                "type": "property_path",
                "property_path": [
                  "form",
                  "meta",
                  "timeEnd"
                ]
              }
            },
            "type": "boolean_expression",
            "property_value": 0
        }
        filters.append(start_date_filter)
    if spec['end_date'] is not None:
        end_date_filter = {
            "operator": "gte",
            "expression": {
              "datatype": "integer",
              "from_date_expression": {
                "datatype": "date",
                "type": "property_path",
                "property_path": [
                  "form",
                  "meta",
                  "timeEnd"
                ]
              },
              "type": "diff_days",
              "to_date_expression": spec['end_date']
            },
            "type": "boolean_expression",
            "property_value": 0
        }
        filters.append(end_date_filter)
    if spec['xmlns'] is not None:
        xmlns_filter = {
            "operator": "eq",
            "type": "boolean_expression",
            "expression": {
                "datatype": "string",
                "type": "property_name",
                "property_name": "xmlns"
            },
            "property_value": spec['xmlns']
        }
        filters.append(xmlns_filter)
    
    spec = {
        "filter_expression": {
            "type": "and",
            "filters": filters
        },
        "type": "filter_items",
        "items_expression": {
            "type": "get_case_forms",
            "case_id_expression": spec['case_id_expression']
        }
    }
    return ExpressionFactory.from_spec(spec, context)
