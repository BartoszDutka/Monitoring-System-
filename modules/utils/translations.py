"""
Translation utilities for the monitoring system
"""
from flask import session

def get_message(key, lang=None):
    """
    Zwraca przetłumaczony komunikat błędu w zależności od języka sesji
    """
    if lang is None:
        lang = session.get('language', 'en')
    
    messages = {
        'en': {
            'invalid_credentials': 'Invalid username or password',
            'missing_credentials': 'Please provide both username and password',
            'user_not_found': 'User not found',
            'error_loading_profile': 'Error loading profile',
            'current_password_required': 'Current password is required to change password',
            'passwords_mismatch': 'New passwords do not match',
            'current_password_incorrect': 'Current password is incorrect',
            'profile_updated': 'Profile updated successfully',
            'no_changes': 'No changes made',
            'error_updating_profile': 'Error updating profile',
            'no_file_selected': 'No file selected',
            'avatar_updated': 'Avatar updated successfully',
            'error_uploading_avatar': 'Error uploading avatar',
            'invalid_file_type': 'Invalid file type. Please use PNG, JPG, JPEG or GIF.',
            'task_title_assignee_required': 'Title and assignee are required',
            'task_created': 'Task created successfully',
            'task_not_found': 'Task not found',
            'cannot_update_task': 'You cannot update this task',
            'task_updated': 'Task updated successfully',
            'cannot_delete_task': 'You cannot delete this task - you can only delete your own tasks',
            'task_deleted': 'Task deleted successfully',
            'access_denied_task': 'Access denied - you can only view your own tasks',
            'cannot_comment_task': 'You cannot comment on this task - you can only comment on your own tasks',
            'comment_empty': 'Comment cannot be empty',
            'comment_added': 'Comment added successfully'
        },
        'pl': {
            'invalid_credentials': 'Nieprawidłowa nazwa użytkownika lub hasło',
            'missing_credentials': 'Proszę podać nazwę użytkownika i hasło',
            'user_not_found': 'Użytkownik nie znaleziony',
            'error_loading_profile': 'Błąd ładowania profilu',
            'current_password_required': 'Obecne hasło jest wymagane do zmiany hasła',
            'passwords_mismatch': 'Nowe hasła nie są identyczne',
            'current_password_incorrect': 'Obecne hasło jest nieprawidłowe',
            'profile_updated': 'Profil zaktualizowany pomyślnie',
            'no_changes': 'Brak zmian',
            'error_updating_profile': 'Błąd aktualizacji profilu',
            'no_file_selected': 'Nie wybrano pliku',
            'avatar_updated': 'Avatar zaktualizowany pomyślnie',
            'error_uploading_avatar': 'Błąd podczas przesyłania avatara',
            'invalid_file_type': 'Nieprawidłowy typ pliku. Proszę użyć PNG, JPG, JPEG lub GIF.',
            'task_title_assignee_required': 'Tytuł i przypisany użytkownik są wymagane',
            'task_created': 'Zadanie utworzone pomyślnie',
            'task_not_found': 'Zadanie nie znalezione',
            'cannot_update_task': 'Nie możesz zaktualizować tego zadania',
            'task_updated': 'Zadanie zaktualizowane pomyślnie',
            'cannot_delete_task': 'Nie możesz usunąć tego zadania - możesz usuwać tylko swoje zadania',
            'task_deleted': 'Zadanie usunięte pomyślnie',
            'access_denied_task': 'Dostęp zabroniony - możesz przeglądać tylko swoje zadania',
            'cannot_comment_task': 'Nie możesz komentować tego zadania - możesz komentować tylko swoje zadania',
            'comment_empty': 'Komentarz nie może być pusty',
            'comment_added': 'Komentarz dodany pomyślnie'
        }
    }
    
    return messages.get(lang, {}).get(key, messages['en'].get(key, key))
