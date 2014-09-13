import copy
import sqlalchemy

def emberify(collection, model=None, many=True):

    def emberify_record(record=None):
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

        # Go through each column and see if there's a foreign key involved
        del_columns = []
        for key, val in record.iteritems():
            column = model.__dict__.get(key)

            # Some sort of relationship
            property = getattr(column, 'property', None)
            if property and type(property) is sqlalchemy.orm.relationships.RelationshipProperty:
                id_column = next(iter(column.property.local_columns))

                # This model is being referenced by something else
                if id_column.primary_key:
                    #TODO: sideload
                    other_ids = []
                    for other_item in val:
                        #FIXME: assuming id is primary key
                        other_ids.append(other_item['id'])
                    record[key] = other_ids

                # This model is referencing something else
                else:
                    #TODO: Sideload
                    record[key] = record[id_column.name]
                    del_columns.append(id_column.name)

        #TODO: sideload instead of delete
        for col in del_columns:
            del(record[col])

    def emberify_single(result=None, **kw):
        emberify_record(result)
        result[collection] = copy.deepcopy(result)
        for key in result.keys():
            if key != collection:
                del(result[key])

    def emberify_many(result=None, **kw):
        # Remove pagination
        for key in result.keys():
            if key != 'objects':
                del(result[key])
        result[collection] = result['objects']
        del(result['objects'])

        # Handle foreign keys
        for item in result[collection]:
            emberify_record(item)

    if many:
        return emberify_many
    return emberify_single
