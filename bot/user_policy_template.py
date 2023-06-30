import json

policy_template_json = '{"IsAdministrator":false,' \
                       '"IsHidden":true,' \
                       '"IsHiddenRemotely":true,' \
                       '"IsHiddenFromUnusedDevices":true,' \
                       '"IsDisabled":false,' \
                       '"BlockedTags":[],' \
                       '"IsTagBlockingModeInclusive":false,' \
                       '"IncludeTags":[],' \
                       '"EnableUserPreferenceAccess":true,' \
                       '"AccessSchedules":[],' \
                       '"BlockUnratedItems":[],' \
                       '"EnableRemoteControlOfOtherUsers":false,' \
                       '"EnableSharedDeviceControl":false,' \
                       '"EnableRemoteAccess":true,' \
                       '"EnableLiveTvManagement":false,' \
                       '"EnableLiveTvAccess":true,' \
                       '"EnableMediaPlayback":true,' \
                       '"EnableAudioPlaybackTranscoding":false,' \
                       '"EnableVideoPlaybackTranscoding":false,' \
                       '"EnablePlaybackRemuxing":false,' \
                       '"EnableContentDeletion":false,' \
                       '"EnableContentDeletionFromFolders":[],' \
                       '"EnableContentDownloading":false,' \
                       '"EnableSubtitleDownloading":false,' \
                       '"EnableSubtitleManagement":false,' \
                       '"EnableSyncTranscoding":false,' \
                       '"EnableMediaConversion":false,' \
                       '"EnabledChannels":[],' \
                       '"EnableAllChannels":true,' \
                       '"EnabledFolders":[],' \
                       '"EnableAllFolders":true,' \
                       '"InvalidLoginAttemptCount":0,' \
                       '"EnablePublicSharing":false,' \
                       '"RemoteClientBitrateLimit":0,' \
                       '"ExcludedSubFolders":[],' \
                       '"SimultaneousStreamLimit":3,' \
                       '"EnabledDevices":[],' \
                       '"EnableAllDevices":true}'

policy_template_dict = json.loads(policy_template_json)
