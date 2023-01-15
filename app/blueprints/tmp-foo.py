
    #stmt = select()
    #x = session.query(Collection.proxy_taxon_id,func.count(Collection.proxy_taxon_id)).group_by(Collection.proxy_taxon_id).all()
    #print(len(x), flush=True)

    import csv
    from app.taxon.models import Taxon
    family_list = Taxon.query.filter(Taxon.rank=='family').all()
    print(len(family_list), flush=True)
    '''
    order_list = []
    order_map = {}
    with open('TaiwanSpecies20220831_UTF8.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['kingdom'] and row['kingdom'] == 'Plantae':
                if item := row['order']:
                    if item not in order_list:
                        order_list.append(item)
                        order_map[item] = row.get('order_c', '')
        print(len(order_list), flush=True)
    '''
    '''
    count = 0
    for x in Collection.query.all():
        count += 1
        ids = [x for x in x.identifications.order_by(Identification.verification_level).all()]
        if len(ids):
            x.last_taxon = '{}|{}'.format(ids[-1].taxon.full_scientific_name if ids[-1].taxon else '', ids[-1].taxon.common_name if ids[-1].taxon else '')
            #x.save()
            session.commit()
            count += 1
            print(count, flush=True)
    '''
