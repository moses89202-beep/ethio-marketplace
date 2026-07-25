from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required 
from .models import *
from .forms import *
from django.http import JsonResponse
from django.core.cache import cache

@login_required
def new_conversation(request, item_pk):
    item = get_object_or_404(Item, pk=item_pk)

    if item.created_by == request.user:
        return redirect('dashboard:index')
    
    conversations = Conversation.objects.filter(item=item).filter(members__in=[request.user.id])

    if conversations:
        return redirect ('chat:detail', pk=conversations.first().id)

    if request.method == 'POST':
        form = ConversationMessageForm(request.POST)

        if form.is_valid():
            conversation = Conversation.objects.create(item=item)
            conversation.members.add(request.user)
            conversation.members.add(item.created_by)
            conversation.save()

            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()


            return redirect('chat:detail', pk=conversation.id)
        
    else:
        form = ConversationMessageForm()
        
    return render(request, 'new.html',{
        'form': form,
    })

@login_required
def inbox(request):
    conversations = Conversation.objects.filter(members__in=[request.user.id])

    return render(request, 'inbox.html', {
        'conversations': conversations,
    })



@login_required
def detail(request, pk):
    conversation = Conversation.objects.filter(members__in=[request.user.id]).get(pk=pk)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    user_is_typing = request.headers.get('X-Is-Typing') == 'true'
    cache_key = f"typing_{conversation.id}_{request.user.id}"
    
    if user_is_typing:
        cache.set(cache_key, True, timeout=3)
    elif request.headers.get('X-Is-Typing') == 'false':
        cache.delete(cache_key)

    other_members = conversation.members.exclude(id=request.user.id)
    other_is_typing = any(cache.get(f"typing_{conversation.id}_{member.id}") for member in other_members)

    if request.method == 'POST':
        form = ConversationMessageForm(request.POST)

        if form.is_valid():
            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()
            conversation.save()

            cache.delete(cache_key)

            if is_ajax:
                return JsonResponse({'status': 'ok'})
            return redirect('chat:detail', pk=pk)

    else:
        form = ConversationMessageForm()

    response = render(request, 'chat/detail.html', {
        'conversation': conversation,
        'form': form,
        'other_is_typing': other_is_typing
    })

    response['X-Receiver-Typing'] = 'true' if other_is_typing else 'false'
    return response