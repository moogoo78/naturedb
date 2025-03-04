from datetime import datetime

from flask import (
    current_app,
)

from docx import Document
from docx.shared import Pt, Mm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _add_label_border(paragraph, border_color="000000", border_size="12"):
    p = paragraph._element
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    for side in ['top', 'left', 'bottom', 'right']:
        border = OxmlElement(f'w:{side}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), border_size)  # Thickness
        border.set(qn('w:space'), '4')       # Space between text and border
        border.set(qn('w:color'), border_color)
        pbdr.append(border)
    pPr.append(pbdr)

def _create_text_between(doc, left, right, font_size):
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Pt(150)
    table.columns[1].width = Pt(90)
    cell_left, cell_right = table.rows[0].cells
    cell_left.paragraphs[0].add_run(left).font.size = Pt(font_size)
    cell_right.paragraphs[0].add_run(right).font.size = Pt(font_size)
    #cell_left.text = left
    #cell_right.text = right
    cell_left.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    cell_right.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    table.rows[0].height = Pt(5) # not work

def _create_label(doc, label_data):
    """Creates a single label with variable height."""
    #print(label_data, flush=True)

    fmap = {
        'l': 11,
        'n': 10,
        's': 9,
    }
    if len(label_data['identifications']) > 1:
        for k, v in enumerate(label_data['identifications'][1:]):
            p = doc.add_paragraph()
            if v['taxon'][0]:
                run = p.add_run(f"{v['taxon'][0]}\n")
                run.bold = True
                run.font.size = Pt(fmap['s'])

            if k == len(label_data['identifications'][1:]) - 1:
                run = p.add_run(f"{v['taxon'][1]}")
            else:
                run = p.add_run(f"{v['taxon'][1]}")
            run.bold = True
            run.font.size = Pt(fmap['s'])

            left = f"Det. by {v['identifier']}" if v.get('identifier') else ''
            right = v['date'] if v.get('date') else ''
            _create_text_between(doc, left, right, fmap['s'])

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{label_data['layout']['header']}")
    run.bold = True
    run.font.size = Pt(fmap['l'])

    if len(label_data['identifications']) > 0:
        if first_id := label_data['identifications'][0]:
            p = doc.add_paragraph()
            run = p.add_run(f"{first_id['taxon'][0]}")
            run.bold = True
            run.font.size = Pt(fmap['s'])

            species_run = p.add_run('\n'+first_id['taxon'][1])
            species_run.bold = True
            species_run.font.size = Pt(fmap['s'])

    loc_p = doc.add_paragraph()
    for k, v in enumerate(label_data['event']['location']['locality']):
        if k == len(label_data['event']['location']['locality']) - 1:
            loc_p.add_run(v).font.size = Pt(fmap['s'])
        else:
            loc_p.add_run(v + "\n").font.size = Pt(fmap['s'])

    _create_text_between(doc, label_data['event']['location']['lonlat'], label_data['event']['location']['elev'], fmap['s'])

    if x := label_data.get('notes'):
        note_p = doc.add_paragraph()
        for k, v in enumerate(x):
            n = v if k == len(x) - 1 else v + "\n"
            note_p.add_run(n).font.size = Pt(fmap['s'])

    if label_data['unit']:
        if x := label_data['unit'].get('type_status'):
            type_p = doc.add_paragraph()
            type_p.add_run(x).font.size = Pt(fmap['s'])

    if label_data['event']['collector'] or label_data['event']['date']:
        _create_text_between(doc, label_data['event']['collector'], label_data['event']['date'], fmap['s'])

    if x:= label_data['event'].get('companion'):
        s = '& ' + ', '.join(x)
        p = doc.add_paragraph()
        p.add_run(s).font.size = Pt(fmap['s'])

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for k, v in enumerate(label_data['layout']['footer']):
        s = v if k == len(label_data['layout']['footer']) - 1 else v + "\n"
        r = footer_p.add_run(s)
        r.bold = True
        r.font.size = Pt(fmap['s'])

    # Final note
    if x := label_data['unit'].get('appendix'):
        appendix_p = doc.add_paragraph()
        #appendix_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for k, v in enumerate(x):
            s = v if k == len(x) - 1 else v + '\n'
            appendix_p.add_run(s).font.size = Pt(fmap['s'])


def get_label_text(entity):
    record = entity['record']
    unit = entity['unit']

    header = ''
    if country := record.get_named_area('COUNTRY'):
        if country.id == 1311:
            header = 'BOTANICAL INVENTORY OF TAIWAN'
        else:
            header = f'PLANTS OF {country.name_en.upper()}'

    ids = []
    for i in record.identifications:
        taxon_family = ''
        taxon_species = ''
        if family := i.taxon.get_higher_taxon('family'):
            taxon_family = family.full_scientific_name
        taxon_species = i.taxon.display_name
        id_data = {
            'taxon': [taxon_family, taxon_species],
        }
        if x := i.identifier:
            id_data.update({'identifier': x.display_name})
        if x := i.date:
            id_data.update({'date': i.get_date_display('%b. %d, %Y')})
        ids.append(id_data)

    locality_list = []
    na = []
    for k, v in record.get_named_area_map().items():
        if v and k != 'COUNTRY':
            na.append(v.named_area.display_name)
    if len(na) > 0:
        locality_list.append(' ,'.join(na))
    if x := record.locality_text:
        locality_list.append(x)
    if x := record.locality_text_en:
        locality_list.append(x)

    lonlat = ''
    elev = ''
    if coordinates := record.get_coordinates('dms'):
        lonlat = f"{coordinates['x_label']}, {coordinates['y_label']}"
    if record.altitude:
        elev = f"Elev. ca. {record.altitude}"
        if x := record.altitude2:
            elev = f'{elev}-{x} m'


    data = {
        'identifications': ids,
        #'notes': notes,
        #'type_status': type_status,
        #'appendix': appendix,
        'layout': {
            'header': header,
            'footer': ['中央研究院植物標本館', 'Herbarium, Academia Sinica, Taipei (HAST)'],
        },
        'event': {
            'collector': '',
            'companion': '',
            'date': '',
            'location': {
                'lonlat': lonlat,
                'elev': elev,
                'locality': locality_list,
            }
        },
        'unit': {},
    }

    collector = ''
    if x := record.collector_id:
        #collector = record.collector.display_name
        collector = record.collector.full_name_en or record.collector.full_name
    if y := record.field_number:
        collector = f'{collector} {y}'
        data['event']['collector'] = collector
    data['event']['people'] = collector
    if x := record.collect_date:
        data['event']['date'] = x.strftime('%b. %d, %Y')
    if x := record.companion_list:
        data['event']['companion'] = x

    # only HAST rules now
    notes = []
    appendix = []
    type_status = ''
    if entity['type'] == 'unit':
        unit_data = {}
        unit = entity['unit']
        if x := unit.get_annotation('add-char'):
            notes.append(unit.get_annotation('add-char').value)

        if x := unit.get_annotation('greenhouse'):
            if x.value:
                appendix.append('Plants of this collection were brought back for cultivation.')

        if p_date := unit.get_annotation('greenhouse_pressed_date'):
            d = ''
            try:
                d = datetime.strptime(p_date.value, '%Y-%m-%d').strftime('%b. %d, %Y')
                appendix.append(f'This specimen was pressed on {d}')
            except:
                current_app.logger.error('greenhouse_pressed_date date format error')

        if unit.type_status:
            data['unit']['type_status'] = f'{unit.type_status.upper()} of {unit.typified_name}'

    for i in entity['assertion_display_list']:
        notes.append(i)

    if x := record.field_note:
        notes.append(x)
    if x := record.field_note_en:
        notes.append(x)

    if len(notes):
        data['notes'] = notes

    if len(appendix):
        data['unit']['appendix'] = appendix

    return data

def make_print_docx(items):

    doc = Document()
    # make A4 size
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(15)
    section.bottom_margin = Mm(15)
    section.left_margin = Mm(15)
    section.right_margin = Mm(15)
    section.column_width = Mm(85)
    #section.start_type

    # set_2_columns
    section._sectPr.xpath('./w:cols')[0].set(qn('w:num'), '2')

    style = doc.styles['Normal']
    style.paragraph_format.line_spacing = 1

    for item in items:
        label_info = get_label_text(item)
        _create_label(doc, label_info)
        doc.add_paragraph()  # Spacing between labels

    return doc
