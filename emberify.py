import copy
import sqlalchemy

def emberify_record(model, record=None, sideload=False):
    """
    Ember expects the reference field to have the ID.  What is being
    recieved by restless is the reference field has the de-referenced data
    and the field that stores the id to the reference is being thrown in as
    well, which causes errors.

    Ember expects:
    {
      posts: [
        {id: 1, user: 27, ...}
      ],
      users: {id: 27, ...} // Optional sideloading
    }
    We're getting:
    {
      posts: [
        {id: 1, user_id: 27, user: {id: 27, name: ...} ...}
    }
    """

    # Go through each column/property on the model and see if there's a foreign
    # key that may be in the result that needs to be rearranged for Ember
    sideload_refs = {}
    for property_name in model.__dict__.keys():

        prop = model.__dict__[property_name]

        # Some sort of relationship property on the model
        if getattr(prop, 'property', None) and type(prop.property) is sqlalchemy.orm.relationships.RelationshipProperty:

            # I dunno man, just magically poking at SQLAlchemy innards to get
            # the column that stores the ID for this relationship proprety
            id_column = next(iter(prop.property.local_columns))

            # If the ID involved in this relationship is the primary_key, then
            # we know that this model is being referenced by something else
            if id_column.primary_key:

                # sideload
                referencing_data = record.get(property_name, [])
                if sideload and referencing_data:

                    # Get the other class so that it can be sideloaded as well
                    other_class = prop.property.mapper.class_
                    for referencing_item in referencing_data:

                        # Get any sideloaded data we can from the referencing class
                        sideload_data = emberify_record(other_class, referencing_item)
                        for model_name, model_data in sideload_data:
                            sideload_refs[model_name] = sideload_refs.get(model_name, []) + model_data

                        # Sideload the models that are referencing this data
                        sideload_refs[property_name] = sideload_refs.get(property_name, []) + [referencing_item]

                # Ember expects a list of reference ids, val is a list of
                # the actual objects, turn into a list of ids
                other_ids = []
                for other_item in referencing_data:
                    #FIXME: assuming 'id' is primary key
                    other_ids.append(other_item['id'])
                record[property_name] = other_ids

            # This relationship is a reference to another model
            else:
                referenced_data = record.get(property_name)
                if sideload and referenced_data:
                    # Plural the refernce name for the sideloaded colection
                    sideload_model = property_name + 's'

                    # Prep the sideload data structure
                    if not sideload_refs.get(sideload_model):
                        sideload_refs[sideload_model] = []

                    # Sideload
                    other_class = prop.property.mapper.class_
                    emberify_func = emberify(sideload_model, other_class, False)
                    emberify_func(referenced_data)
                    sideload_refs[sideload_model].append(referenced_data[sideload_model])

                # Ember expects the referenced model to be an ID and not the
                # actual data for the model being referenced
                if record.get(id_column.name):
                    record[property_name] = record[id_column.name]
                    del record[id_column.name]

    return sideload_refs

def emberify(collection, model=None, many=True):

    def emberify_single(result=None, **kw):
        # Modify data structure to match what ember expects and get the data
        # the should be sideloaded
        sideload = emberify_record(model, result, sideload=True)
        result[collection] = copy.deepcopy(result)
        for key in result.keys():
            if key != collection:
                del(result[key])

        # Sideload data into the result
        for ref_model, data in sideload.iteritems():
            result[ref_model] = data

    def emberify_many(result=None, **kw):
        # Remove pagination
        for key in result.keys():
            if key != 'objects':
                del(result[key])
        result[collection] = result['objects']
        del(result['objects'])

        # Handle foreign keys
        for item in result[collection]:
            sideload = emberify_record(model, item, sideload=True)
            for ref_model, data in sideload.iteritems():
                if not result.get(ref_model):
                    result[ref_model] = data
                else:
                    result[ref_model] += data

    if many:
        return emberify_many
    return emberify_single
