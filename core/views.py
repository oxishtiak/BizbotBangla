from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from datetime import date, timedelta
import json, csv
from .models import Shop, Product, Transaction, Baki

_DIGIT_MAP = str.maketrans('0123456789.-', '০১২৩৪৫৬৭৮৯.-')
def to_bengali_nums(value):
    return str(value).translate(_DIGIT_MAP)

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        u = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if u: login(request, u); return redirect('dashboard')
        messages.error(request, 'ভুল username বা password!')
    return render(request, 'auth/login.html')

def register_view(request):
    if request.method == 'POST':
        uname = request.POST['username']
        if User.objects.filter(username=uname).exists():
            messages.error(request, 'এই username আগে থেকেই আছে!'); return render(request,'auth/register.html')
        u = User.objects.create_user(username=uname, password=request.POST['password'])
        Shop.objects.create(user=u, shop_name=request.POST['shop_name'],
            owner_name=request.POST['owner_name'], phone=request.POST.get('phone',''))
        login(request, u); return redirect('dashboard')
    return render(request, 'auth/register.html')

def logout_view(request):
    logout(request); return redirect('login')

def _calc_balance(shop, txns, baki_qs):
    """real balance = sell - buy - pending baki"""
    sell  = txns.filter(transaction_type='sell').aggregate(s=Sum('total_amount'))['s'] or 0
    buy   = txns.filter(transaction_type='buy').aggregate(s=Sum('total_amount'))['s'] or 0
    baki  = baki_qs.aggregate(s=Sum('amount'))['s'] or 0
    return sell - buy - baki

@login_required
def dashboard(request):
    shop = get_object_or_404(Shop, user=request.user)
    today = date.today()
    month_start = today.replace(day=1)
    txns = Transaction.objects.filter(shop=shop)

    def agg(qs, t): return qs.filter(transaction_type=t).aggregate(s=Sum('total_amount'))['s'] or 0

    m = txns.filter(date__gte=month_start)
    sell_m = agg(m,'sell'); buy_m = agg(m,'buy')

    # ✅ real balance = sell - buy - pending baki (এই মাসের)
    baki_m     = Baki.objects.filter(shop=shop, date__gte=month_start)
    baki_total_m = baki_m.aggregate(s=Sum('amount'))['s'] or 0
    profit_m   = sell_m - buy_m - baki_total_m

    sell_d = agg(txns.filter(date=today),'sell')
    buy_d  = agg(txns.filter(date=today),'buy')
    baki_d = Baki.objects.filter(shop=shop, date=today).aggregate(s=Sum('amount'))['s'] or 0
    real_balance_d = sell_d - buy_d - baki_d

    labels, sell_w, buy_w = [], [], []
    for i in range(6,-1,-1):
        d = today - timedelta(days=i)
        labels.append(d.strftime('%a')); dq = txns.filter(date=d)
        sell_w.append(float(agg(dq,'sell'))); buy_w.append(float(agg(dq,'buy')))

    low_stock  = [p for p in Product.objects.filter(shop=shop) if p.is_low_stock]
    recent     = txns[:6]
    baki_total = Baki.objects.filter(shop=shop).aggregate(s=Sum('amount'))['s'] or 0

    return render(request,'core/dashboard.html',{
        'shop':shop, 'sell_m':sell_m, 'buy_m':buy_m,
        'profit_m':profit_m,           # ✅ real balance (baki বাদ দিয়ে)
        'baki_total_m': baki_total_m,  # ✅ এই মাসের pending বাকি
        'baki_total': baki_total,      # ✅ সব মিলিয়ে pending বাকি
        'sell_d':sell_d, 'buy_d':buy_d,
        'real_balance_d': real_balance_d,
        'low_stock':low_stock, 'recent':recent,
        'chart_labels':json.dumps(labels),
        'chart_sell':json.dumps(sell_w),
        'chart_buy':json.dumps(buy_w),
        'product_count':Product.objects.filter(shop=shop).count(),
    })

@login_required
def voice_sell(request):
    shop = get_object_or_404(Shop, user=request.user)
    products = Product.objects.filter(shop=shop)
    return render(request,'core/voice_sell.html',{'shop':shop,'products':products})

@login_required
def voice_buy(request):
    shop = get_object_or_404(Shop, user=request.user)
    products = Product.objects.filter(shop=shop)
    return render(request,'core/voice_buy.html',{'shop':shop,'products':products})

@login_required
def save_transaction(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False})
    shop = get_object_or_404(Shop, user=request.user)
    data = json.loads(request.body)

    product    = None
    pid        = data.get('product_id')
    pname      = data.get('product_name', '').strip()
    qty        = float(data.get('quantity') or 0)
    unit_price = float(data.get('unit_price') or 0)
    total      = float(data.get('total_amount') or 0)
    unit       = data.get('unit', 'পিস')
    tx_type    = data.get('type')

    if tx_type not in ('buy', 'sell'):
        return JsonResponse({'ok': False}, status=400)
    if qty <= 0 or total <= 0:
        return JsonResponse({'ok': False}, status=400)

    if tx_type == 'sell':
        if pid:
            try:
                product = Product.objects.get(id=pid, shop=shop)
                product.stock = max(0, product.stock - qty)
                calc_up = unit_price or (total / qty if qty else 0)
                if calc_up > 0:
                    product.sell_price = calc_up
                product.save()
            except Product.DoesNotExist:
                pass

    elif tx_type == 'buy':
        if pid:
            try:
                product = Product.objects.get(id=pid, shop=shop)
            except Product.DoesNotExist:
                pass
        if not product and pname:
            product, created = Product.objects.get_or_create(
                shop=shop, name=pname,
                defaults={'stock':0,'unit':unit,'buy_price':unit_price,'sell_price':0,'low_stock_alert':0}
            )
            if not created:
                if unit and unit != 'পিস': product.unit = unit
                if unit_price: product.buy_price = unit_price
                product.save()
        if product and qty:
            product.stock += qty
            if unit_price: product.buy_price = unit_price
            if unit and unit != 'পিস' and not product.unit: product.unit = unit
            product.save()

    Transaction.objects.create(
        shop=shop, product=product, transaction_type=tx_type,
        description=data.get('description',''),
        quantity=qty, unit_price=unit_price, total_amount=total, date=date.today()
    )
    return JsonResponse({'ok': True})

@login_required
def records(request):
    shop = get_object_or_404(Shop, user=request.user)
    today = date.today()
    period = request.GET.get('period', 'daily')
    if period == 'weekly':
        start = today - timedelta(days=today.weekday())
    elif period == 'monthly':
        start = today.replace(day=1)
    else:
        start = today

    txns       = Transaction.objects.filter(shop=shop, date__gte=start)
    sell_total = txns.filter(transaction_type='sell').aggregate(s=Sum('total_amount'))['s'] or 0
    buy_total  = txns.filter(transaction_type='buy').aggregate(s=Sum('total_amount'))['s'] or 0
    baki_list  = Baki.objects.filter(shop=shop, date__gte=start)
    baki_total = baki_list.aggregate(s=Sum('amount'))['s'] or 0

    # ✅ real balance = sell - buy - pending baki
    real_balance = sell_total - buy_total - baki_total
    profit       = sell_total - buy_total   # gross profit (baki ছাড়া)

    return render(request, 'core/records.html', {
        'shop':shop, 'txns':txns,
        'sell_total':sell_total, 'buy_total':buy_total,
        'profit':profit,
        'real_balance':real_balance,       # ✅ baki বাদ দেওয়া balance
        'is_profit': real_balance >= 0,
        'period':period, 'today':today,
        'baki_list':baki_list,
        'baki_total':baki_total,
    })

@login_required
def delete_transaction(request, pk):
    shop = get_object_or_404(Shop, user=request.user)
    t = get_object_or_404(Transaction, pk=pk, shop=shop)
    if t.product:
        if t.transaction_type == 'sell': t.product.stock += t.quantity
        else: t.product.stock = max(0, t.product.stock - t.quantity)
        t.product.save()
    t.delete()
    messages.success(request, 'লেনদেন মুছে ফেলা হয়েছে!')
    return redirect(request.META.get('HTTP_REFERER', 'records'))

@login_required
def reset_transactions(request):
    if request.method == 'POST':
        shop = get_object_or_404(Shop, user=request.user)
        period = request.POST.get('period', 'daily')
        today  = date.today()
        if period == 'weekly':
            start = today - timedelta(days=today.weekday())
        elif period == 'monthly':
            start = today.replace(day=1)
        else:
            start = today
        Transaction.objects.filter(shop=shop, date__gte=start).delete()
        messages.success(request, 'লেনদেন মুছে ফেলা হয়েছে!')
    return redirect(f'/records/?period={request.POST.get("period","daily")}')

@login_required
def inventory(request):
    shop = get_object_or_404(Shop, user=request.user)
    products = Product.objects.filter(shop=shop)
    return render(request,'core/inventory.html',{'shop':shop,'products':products})

@login_required
def add_product(request):
    shop = get_object_or_404(Shop, user=request.user)
    if request.method == 'POST':
        Product.objects.create(
            shop=shop, name=request.POST['name'],
            stock=float(request.POST.get('stock',0)),
            unit=request.POST.get('unit','পিস'),
            buy_price=float(request.POST.get('buy_price',0)),
            sell_price=float(request.POST.get('sell_price',0)),
            low_stock_alert=float(request.POST.get('low_stock_alert',0))
        )
        messages.success(request,'পণ্য যোগ হয়েছে!')
        return redirect('inventory')
    return render(request,'core/add_product.html',{'shop':shop})

@login_required
def edit_product(request, pk):
    shop = get_object_or_404(Shop, user=request.user)
    p = get_object_or_404(Product, pk=pk, shop=shop)
    if request.method == 'POST':
        p.name=request.POST['name']; p.stock=float(request.POST.get('stock',0))
        p.unit=request.POST.get('unit','পিস')
        p.buy_price=float(request.POST.get('buy_price',0))
        p.sell_price=float(request.POST.get('sell_price',0))
        p.low_stock_alert=float(request.POST.get('low_stock_alert',0))
        p.save()
        messages.success(request,'পণ্য আপডেট হয়েছে!')
        return redirect('inventory')
    return render(request,'core/edit_product.html',{'shop':shop,'product':p})

@login_required
def delete_product(request, pk):
    shop = get_object_or_404(Shop, user=request.user)
    get_object_or_404(Product, pk=pk, shop=shop).delete()
    messages.success(request,'পণ্য মুছে ফেলা হয়েছে!')
    return redirect('inventory')

@login_required
def export_csv(request):
    shop = get_object_or_404(Shop, user=request.user)
    period = request.GET.get('period', 'daily')
    today  = date.today()
    if period == 'weekly':
        start = today - timedelta(days=today.weekday()); period_label = 'সাপ্তাহিক'
    elif period == 'monthly':
        start = today.replace(day=1); period_label = 'মাসিক'
    else:
        start = today; period_label = 'দৈনিক'

    txns       = Transaction.objects.filter(shop=shop, date__gte=start)
    sell_total = txns.filter(transaction_type='sell').aggregate(s=Sum('total_amount'))['s'] or 0
    buy_total  = txns.filter(transaction_type='buy').aggregate(s=Sum('total_amount'))['s'] or 0
    profit     = sell_total - buy_total
    baki_list  = Baki.objects.filter(shop=shop, date__gte=start)
    baki_total = baki_list.aggregate(s=Sum('amount'))['s'] or 0
    real_balance = sell_total - buy_total - baki_total

    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="hisab_{period}.csv"'
    resp.write('\ufeff')
    w = csv.writer(resp)
    w.writerow(['--- হিসাবের সারসংক্ষেপ ---', period_label])
    w.writerow(['মোট বিক্রয়',    f'৳{to_bengali_nums(sell_total)}'])
    w.writerow(['মোট ক্রয়',     f'৳{to_bengali_nums(buy_total)}'])
    w.writerow(['মোট বাকি (পেন্ডিং)', f'৳{to_bengali_nums(baki_total)}'])
    w.writerow(['নিট লাভ/ক্ষতি', f'{"✅ লাভ" if profit >= 0 else "❌ ক্ষতি"}: ৳{to_bengali_nums(abs(profit))}'])
    w.writerow(['প্রকৃত ব্যালেন্স (বাকি বাদে)', f'৳{to_bengali_nums(real_balance)}'])
    w.writerow([]); w.writerow([])
    w.writerow(['তারিখ','ধরন','পণ্য','পরিমাণ','একক','মূল্য/একক','মোট টাকা','বিবরণ'])
    for t in txns:
        w.writerow([
            f"'{to_bengali_nums(t.date.strftime('%d-%m-%Y'))}",
            t.get_transaction_type_display(),
            t.product.name if t.product else '',
            to_bengali_nums(round(t.quantity,2)),
            t.product.unit if t.product else '',
            to_bengali_nums(round(t.unit_price,2)),
            to_bengali_nums(round(t.total_amount,2)),
            t.description,
        ])
    if baki_list.exists():
        w.writerow([]); w.writerow([])
        w.writerow(['--- বাকির তালিকা ---'])
        w.writerow(['তারিখ','নাম','পণ্য','পরিমাণ','টাকা','বিবরণ'])
        for b in baki_list:
            w.writerow([
                f"'{to_bengali_nums(b.date.strftime('%d-%m-%Y'))}",
                b.name,
                b.product.name if b.product else '',
                to_bengali_nums(round(b.quantity,2)) if b.quantity else '',
                to_bengali_nums(round(b.amount,2)),
                b.note,
            ])
        w.writerow(['মোট বাকি','','','', to_bengali_nums(round(baki_total,2)),''])
    return resp

@login_required
def products_json(request):
    shop = get_object_or_404(Shop, user=request.user)
    data = list(Product.objects.filter(shop=shop).values('id','name','unit','sell_price','buy_price','stock'))
    return JsonResponse({'products': data})

# ── বাকির হিসাব ─────────────────────────────────────────────────────────────

@login_required
def baki_list(request):
    shop = get_object_or_404(Shop, user=request.user)
    bakis      = Baki.objects.filter(shop=shop)
    baki_total = bakis.aggregate(s=Sum('amount'))['s'] or 0
    products   = Product.objects.filter(shop=shop)
    return render(request, 'core/baki.html', {
        'shop':shop, 'bakis':bakis,
        'baki_total':baki_total,
        'products':products,
        'today': date.today(),
    })

@login_required
def baki_add(request):
    if request.method == 'POST':
        shop     = get_object_or_404(Shop, user=request.user)
        name     = request.POST.get('name','').strip()
        amount   = float(request.POST.get('amount', 0))
        note     = request.POST.get('note','').strip()
        txn_date = request.POST.get('date', str(date.today()))
        pid      = request.POST.get('product')
        qty      = float(request.POST.get('quantity') or 0)

        if not name or amount <= 0:
            messages.error(request, 'নাম এবং টাকার পরিমাণ দিন!')
            return redirect('baki_list')

        product = None
        if pid:
            try:
                product = Product.objects.get(id=pid, shop=shop)
                # ✅ stock থেকে কাটো
                if qty > 0:
                    product.stock = max(0, product.stock - qty)
                    product.save()
            except Product.DoesNotExist:
                pass

        Baki.objects.create(
            shop=shop, name=name, amount=amount,
            note=note, date=txn_date,
            product=product, quantity=qty,
        )
        messages.success(request, f'{name} — ৳{amount} বাকি যোগ হয়েছে!')
    return redirect('baki_list')

@login_required
def baki_delete(request, pk):
    shop = get_object_or_404(Shop, user=request.user)
    b    = get_object_or_404(Baki, pk=pk, shop=shop)
    name   = b.name
    amount = b.amount

    # ✅ পরিশোধ হলে stock ফেরত দেওয়ার দরকার নেই
    # কারণ বাকি দেওয়ার সময়ই stock কাটা হয়েছিল
    # শুধু baki record delete করলেই balance ঠিক হয়ে যাবে

    b.delete()
    messages.success(request, f'{name} এর ৳{amount} বাকি পরিশোধ হয়েছে! ব্যালেন্সে যোগ হয়েছে।')
    return redirect('baki_list')