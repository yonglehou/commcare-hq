from corehq.apps.userreports.expressions.factory import ExpressionFactory
from corehq.apps.userreports.specs import TypeProperty
from dimagi.ext.jsonobject import JsonObject, DictProperty

class GetCaseFormsByDateSpec(JsonObject):
    type = TypeProperty('get_case_forms_by_date')
    case_id_expression = DefaultProperty(required=True)
    start_date = DefaultProperty()
    end_date = DefaultProperty()
    xmlns = DefaultProperty()
    
def get_case_forms_by_date(spec, context):
    GetCaseFormsByDateSpec.wrap(spec)  # this is just for validation
    spec = {
        
        
        
        
        "type": "related_doc",
        "related_doc_type": "Location",
        "doc_id_expression": spec['location_id_expression'],
        "value_expression": {
            "type": "array_index",
            'array_expression': {
                'type': 'property_name',
                'property_name': 'lineage'
            },
            'index_expression': 0,
        }
    }
    return ExpressionFactory.from_spec(spec)
    


