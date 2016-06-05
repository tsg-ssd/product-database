import logging
import tempfile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.shortcuts import redirect, render
from django.utils.timezone import timedelta, datetime, get_current_timezone

from app.config.models import NotificationMessage
from app.productdb import utils as app_util
from app.productdb.excel_import import ImportProductsExcelFile
from app.productdb.forms import ImportProductsFileUploadForm
from app.productdb.models import Product
from app.productdb.models import Vendor

from django_project.utils import login_required_if_login_only_mode

logger = logging.getLogger(__name__)


def home(request):
    """view for the homepage of the Product DB

    :param request:
    :return:
    """
    if login_required_if_login_only_mode(request):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    context = {
        "recent_events": NotificationMessage.objects.filter(
            created__gte=datetime.now(get_current_timezone()) - timedelta(days=14)
        ).order_by('-created')[:5]
    }

    return render(request, "productdb/home.html", context=context)


def about_view(request):
    """about view

    :param request:
    :return:
    """
    if login_required_if_login_only_mode(request):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    return render(request, "productdb/about.html", context={})


def browse_vendor_products(request):
    """Browse vendor specific products in the database

    :param request:
    :return:
    """
    if login_required_if_login_only_mode(request):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    context = {
        "vendors": Vendor.objects.all()
    }
    selected_vendor = ""

    if request.method == "POST":
        selected_vendor = request.POST['vendor_selection']
    else:
        default_vendor = "Cisco Systems"
        for vendor in context['vendors']:
            if vendor.name == default_vendor:
                selected_vendor = vendor.id
                break

    context['vendor_selection'] = selected_vendor

    return render(request, "productdb/browse/view_products_by_vendor.html", context=context)


def browse_all_products(request):
    """Browse all products in the database

    :param request:
    :return:
    """
    if login_required_if_login_only_mode(request):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    return render(request, "productdb/browse/view_products.html", context={})


def bulk_eol_check(request):
    """view that executes and handles the Bulk EoL check function

    :param request:
    :return:
    """
    if login_required_if_login_only_mode(request):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    context = {}

    if request.method == "POST":
        db_queries = request.POST['db_query'].splitlines()

        # clean POST db queries
        clean_db_queries = []
        for q in db_queries:
            clean_db_queries.append(q.strip())
        db_queries = filter(None, clean_db_queries)

        # detailed product results
        query_result = []
        # result statistics
        result_stats = dict()
        # queries, that are not found in the database or that are not affected by an EoL announcement
        skipped_queries = dict()

        for query in db_queries:
            q_result_counter = 0
            found_but_no_eol_announcement = False
            db_result = Product.objects.filter(product_id=query.strip())

            # go through the database results
            for element in db_result:
                q_result_counter += 1

                # check if the product is affected by an EoL announcement
                if element.eol_ext_announcement_date is None:
                    found_but_no_eol_announcement = True

                # don't add duplicates to query result, create statistical element
                if element.product_id not in result_stats.keys():
                    query_result.append(app_util.normalize_date(element))
                    result_stats[element.product_id] = dict()
                    result_stats[element.product_id]['count'] = 1
                    result_stats[element.product_id]['product'] = element
                    result_stats[element.product_id]['state'] = element.current_lifecycle_states

                # increment statistics
                else:
                    result_stats[element.product_id]['count'] += 1

            # classify the query results
            if (q_result_counter == 0) or found_but_no_eol_announcement:
                if (q_result_counter == 0) and not found_but_no_eol_announcement:
                    q_res_str = "Not found in database"

                if found_but_no_eol_announcement:
                    q_res_str = "no EoL announcement found"

                else:
                    # add queries without result to the stats and the counter
                    if query not in result_stats.keys():
                        result_stats[query] = dict()
                        result_stats[query]['state'] = ["Not found in database"]
                        result_stats[query]['product'] = dict()
                        result_stats[query]['product']['product_id'] = query
                        result_stats[query]['count'] = 1
                    else:
                        result_stats[query]['count'] += 1

                # ignore duplicates
                if query not in skipped_queries.keys():
                    skipped_queries[query] = {
                        "query": query.strip(),
                        "result": q_res_str
                    }

        context['query_result'] = query_result
        context['result_stats'] = result_stats
        context['skipped_queries'] = skipped_queries

        # simply display an error message if no result is found
        if len(query_result) == 0:
            context['query_no_result'] = True

    return render(request, "productdb/do/bulk_eol_check.html", context=context)


@login_required()
@permission_required('is_superuser')
def import_products(request):
    """view for the import of products using Excel

    :param request:
    :return:
    """
    context = {}
    if request.method == "POST":
        form = ImportProductsFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # file is valid, execute the import
            uploaded_file = request.FILES['excel_file']

            tmp = tempfile.NamedTemporaryFile(suffix="." + uploaded_file.name.split(".")[-1])

            uploaded_file.open()
            tmp.write(uploaded_file.read())

            try:
                import_products_excel = ImportProductsExcelFile(tmp.name)
                import_products_excel.verify_file()
                import_products_excel.import_products_to_database()

                context['import_valid_imported_products'] = import_products_excel.valid_imported_products
                context['import_invalid_products'] = import_products_excel.invalid_products
                context['import_messages'] = import_products_excel.import_result_messages
                context['import_result'] = "success"

            except Exception as ex:
                msg = "unexpected error occurred during import (%s)" % ex
                logger.error(msg, ex)
                context['import_messages'] = msg
                context['import_result'] = "error"

            finally:
                tmp.close()

    else:
        form = ImportProductsFileUploadForm()

    context['form'] = form

    return render(request, "productdb/import/import_products.html", context=context)
