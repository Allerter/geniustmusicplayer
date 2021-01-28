import random
import string

from kivy.logger import Logger
from jnius import autoclass
from android import api_version


Logger.debug('SERVICE: Execution started.')

# Given a media session and its context (usually the component containing the session)
# Create a NotificationCompat.Builder

# Get the session's metadata
RDrawable = autoclass('android.R$drawable')
RString = autoclass('android.R$string')
NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
MediaButtonReceiver = autoclass('androidx.media.session.MediaButtonReceiver')
MediaSession = autoclass('android.media.session.MediaSession')
NotificationCompatAction = autoclass("androidx.core.app.NotificationCompat$Action")
NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
PlaybackStateCompat = autoclass("android.support.v4.media.session.PlaybackStateCompat")
NotificationManager = autoclass("android.app.NotificationManager")
PythonActivity = autoclass('org.kivy.android.PythonActivity')
NotificationChannel = autoclass('android.app.NotificationChannel')
# service = autoclass('org.kivy.android.PythonService').mService
service = autoclass('org.allerter.geniustmusicplayer.ServiceMyservice').mService

mediaSession = MediaSession()
controller = mediaSession.getController()
mediaMetadata = controller.getMetadata()
description = mediaMetadata.getDescription()

app_context = service.getApplication().getApplicationContext()

if api_version >= 26:
    channel_id = ''.join(random.choices(string.ascii_letters, k=10))
    channel_name = 'GTPlayer'
    channel_importance = NotificationManager.IMPORTANCE_DEFAULT
    channel = NotificationChannel(channel_id, channel_name, channel_importance)
    channel.setDescription('GeniusT Music Player')
    NotificationManagerClass = autoclass('android.app.NotificationManager.class')
    notificationManager = service.getSystemService(NotificationManagerClass)
    notificationManager.createNotificationChannel(channel)
    builder = NotificationCompatBuilder(app_context, channel_id)
else:
    builder = NotificationCompatBuilder(app_context)

IconDrawable = autoclass("{}.R$drawable".format(service.getPackageName()))
icon = getattr(IconDrawable, 'icon')
(builder
    # Add the metadata for the currently playing track
    .setContentTitle('Lane Boy')
    .setContentText('Twenty One Pilots')
    .setSubText('Song')
    .setLargeIcon(icon)

    # Enable launching the player by clicking the notification
    .setContentIntent(controller.getSessionActivity())

    # Stop the service when the notification is swiped away
    # .setDeleteIntent(MediaButtonReceiver.buildMediaButtonPendingIntent(
    #    context,
    #    PlaybackStateCompat.ACTION_STOP))

    # Make the transport controls visible on the lockscreen
    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)

    # Add an app icon and set its accent color
    # Be careful about the color
    .setSmallIcon(icon)
    # .setColor(ContextCompat.getColor(context, R.color.primaryDark))
 )
# Add a pause button
pause_intent = MediaButtonReceiver.buildMediaButtonPendingIntent(
    app_context,
    PlaybackStateCompat.ACTION_PLAY_PAUSE
)
action = NotificationCompatAction(
    RDrawable.pause, 'Pause',  # getString(R.string.pause),
    pause_intent
)
builder.addAction(action)

# Take advantage of MediaStyle features
# .setStyle(new MediaStyle()
#          .setMediaSession(mediaSession.getSessionToken())
#          .setShowActionsInCompactView(0)

#          # Add a cancel button
#          .setShowCancelButton(true)
#          .setCancelButtonIntent(MediaButtonReceiver.buildMediaButtonPendingIntent(
#          context,
#          PlaybackStateCompat.ACTION_STOP)))

# Display the notification and place the service in the foreground
service.startForeground(1, builder.build())
Logger.debug('SERIVCE: Execution finished.')