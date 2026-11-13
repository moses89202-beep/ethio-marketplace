from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format as date_format
from django.views.decorators.http import require_POST

from items.models import Item
from .forms import ConversationMessageForm
from .models import Conversation, ConversationMessage

MAX_HISTORY = 100  # messages loaded when a conversation is opened


# ---------------------------------------------------------------- helpers

def get_user_conversation(request, pk):
    # 404 if it doesn't exist or the user isn't a member
    return get_object_or_404(Conversation, pk=pk, members=request.user)


def typing_key(conversation_id, user_id):
    return f"typing_{conversation_id}_{user_id}"


def format_when(dt):
    local = timezone.localtime(dt)
    if local.date() == timezone.localdate():
        return date_format(local, 'g:i A')
    return date_format(local, 'M j')


def user_conversations(user):
    """The user's conversations (newest activity first) with last-message info in one query."""
    last = ConversationMessage.objects.filter(conversation=OuterRef('pk')).order_by('-id')
    return (
        Conversation.objects.filter(members=user)
        .select_related('item')
        .prefetch_related('members')
        .annotate(
            last_id=Subquery(last.values('id')[:1]),
            last_content=Subquery(last.values('content')[:1]),
            last_sender_id=Subquery(last.values('created_by_id')[:1]),
        )
    )


def serialize_conversation(c, user):
    other = next((m for m in c.members.all() if m.id != user.id), None)
    return {
        'id': c.id,
        'other': other.username if other else 'Deleted user',
        'item_id': c.item_id,
        'item': c.item.name,
        'item_url': reverse('items:detail', args=[c.item_id]),
        'picture': c.item.picture.url if c.item.picture else None,
        'preview': ' '.join((c.last_content or '').split())[:80],
        'last_id': c.last_id or 0,
        'last_from_me': c.last_sender_id == user.id,
        'when': format_when(c.modified_at),
    }


def serialize_message(m, user):
    return {
        'id': m.id,
        'content': m.content,
        'username': m.created_by.username,
        'mine': m.created_by_id == user.id,
        'time': date_format(timezone.localtime(m.created_at), 'g:i A'),
    }


def render_app(request, active_id=None, new_item=None):
    """Every chat URL renders this same single page; JS takes over from here."""
    conversations = [serialize_conversation(c, request.user) for c in user_conversations(request.user)]

    pending = None
    if new_item is not None:
        price = format(new_item.price, ',.2f').rstrip('0').rstrip('.')
        pending = {
            'id': new_item.id,
            'name': new_item.name,
            'price': price,
            'picture': new_item.picture.url if new_item.picture else None,
            'seller': new_item.created_by.username,
            'url': reverse('items:detail', args=[new_item.id]),
        }

    boot = {
        'userId': request.user.id,
        'base': reverse('chat:inbox'),
        'browseUrl': reverse('items:items'),
        'activeId': active_id,
        'newItem': pending,
        'conversations': conversations,
    }
    return render(request, 'chat.html', {'boot': boot})


# ------------------------------------------------------------------ pages

@login_required
def inbox(request):
    return render_app(request)


@login_required
def detail(request, pk):
    get_user_conversation(request, pk)  # 404 for non-members
    return render_app(request, active_id=pk)


@login_required
def new_conversation(request, item_pk):
    item = get_object_or_404(Item.objects.select_related('created_by'), pk=item_pk)

    if item.created_by == request.user:
        return redirect('dashboard:index')

    existing = Conversation.objects.filter(item=item, members=request.user).first()

    if request.method == 'POST':
        if existing:  # e.g. double-click: just point the page at the existing thread
            return JsonResponse({'id': existing.id})

        form = ConversationMessageForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'status': 'error'}, status=400)

        conversation = Conversation.objects.create(item=item)
        conversation.members.add(request.user, item.created_by)

        message = form.save(commit=False)
        message.conversation = conversation
        message.created_by = request.user
        message.save()
        return JsonResponse({'id': conversation.id})

    if existing:
        return redirect('chat:detail', pk=existing.id)

    return render_app(request, new_item=item)


# ---------------------------------------------------------------- JSON API

@login_required
def sync(request):
    """
    One poll does everything: refreshes the conversation list and, if a thread is open,
    returns its new messages and the typing state.
    Query params: active=<conversation id>, after=<last message id seen>, typing=0|1
    """
    user = request.user
    conversations = list(user_conversations(user))

    def to_int(name):
        try:
            return int(request.GET.get(name, 0))
        except ValueError:
            return 0

    active_id = to_int('active')
    after = to_int('after')
    active = next((c for c in conversations if c.id == active_id), None)

    data = {
        'conversations': [serialize_conversation(c, user) for c in conversations],
        'active': active.id if active else None,
        'after': after,
        'messages': [],
        'other_is_typing': False,
    }

    if active:
        key = typing_key(active.id, user.id)
        if request.GET.get('typing') == '1':
            cache.set(key, True, timeout=5)
        else:
            cache.delete(key)

        other_ids = [m.id for m in active.members.all() if m.id != user.id]
        data['other_is_typing'] = any(cache.get(typing_key(active.id, uid)) for uid in other_ids)

        messages = active.messages.select_related('created_by')
        if after:
            batch = list(messages.filter(id__gt=after).order_by('id')[:200])
        else:
            batch = list(messages.order_by('-id')[:MAX_HISTORY])[::-1]
        data['messages'] = [serialize_message(m, user) for m in batch]

    return JsonResponse(data)


@login_required
@require_POST
def send(request, pk):
    conversation = get_user_conversation(request, pk)
    form = ConversationMessageForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'status': 'error'}, status=400)

    message = form.save(commit=False)
    message.conversation = conversation
    message.created_by = request.user
    message.save()

    # bump the thread to the top of everyone's list
    Conversation.objects.filter(pk=conversation.pk).update(modified_at=timezone.now())
    cache.delete(typing_key(conversation.id, request.user.id))

    return JsonResponse({'status': 'ok', 'id': message.id})