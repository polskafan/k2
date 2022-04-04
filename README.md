# k2
Making a Kettler Ergoracer smart

## MQTT Topics
|Topic                      |Publisher        |Description                                                    |Subscriber       |
|---------------------------|-----------------|---------------------------------------------------------------|-----------------|
|k2/status/controller       |ControllerManager|MQTT status of the Controller component                        |                 |
|k2/controller/trackMode    |ControllerManager|Currently active controller sub component                      |UI               |
|k2/controller/cmnd/track   |UI               |Selects currently active controller component and loads a track|ControllerManager|
|                           |                 |                                                               |                 |
|k2/controller/tracks/gpx   |GPXController    |List of available GPX tracks                                   |UI               |
|k2/controller/tracks/komoot|KomootController |List of available Komoot tracks                                |UI               |
|                           |                 |                                                               |                 |
|k2/controller/track        |XYZController    |Currently active track                                         |UI               |
|k2/controller/location     |XYZController    |Location information at the current distance                   |UI, Logger       |
|                           |                 |                                                               |                 |
|k2/status/kettler          |Kettler          |MQTT status of the Kettler component                           |                 |
|k2/kettler/data            |Kettler          |Current data of the Kettler bike                               |ControllerManager|
|k2/kettler/cmnd/power      |XYZController    |Set the target power of the Kettler bike                       |Kettler          |
|k2/kettler/cmnd/reset      |ControllerManager|Reset the Kettler bike                                         |Kettler          |
|                           |                 |                                                               |                 |
|k2/status/logger           |Logger           |MQTT status of the Logger component                            |                 |
|k2/logger/data             |Logger           |Current status of the log                                      |                 |
|k2/logger/cmnd/start       |XYZController    |Start to log data                                              |Logger           |
|k2/logger/cmnd/stop        |XYZController    |Stop to log data                                               |Logger           |
|                           |                 |                                                               |                 |
|k2/status/heartrate        |Heartrate        |MQTT status of the Heartrate component                         |                 |
|k2/heartrate/connected     |Heartrate        |Connection status of the heartrate device                      |Logger, UI       |
|k2/heartrate/location      |Heartrate        |Body location of the heartrate device                          |UI               |
|k2/heartrate/data          |Heartrate        |Current data of the heartrate device                           |Logger, UI       |
