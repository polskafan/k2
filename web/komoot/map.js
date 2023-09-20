/**
 * Created by Timo on 24.09.2016.
 */

var maps = {};

function initializeMap() {
    var mapStyle = new google.maps.StyledMapType([
            {elementType: 'geometry', stylers: [{color: '#242f3e'}]},
            {elementType: 'labels.text.stroke', stylers: [{color: '#242f3e'}]},
            {elementType: 'labels.text.fill', stylers: [{color: '#746855'}]},
            {
              featureType: 'administrative.locality',
              elementType: 'labels.text.fill',
              stylers: [{color: '#d59563'}]
            },
            {
              featureType: 'poi',
              elementType: 'labels.text.fill',
              stylers: [{color: '#d59563'}]
            },
            {
              featureType: 'poi.park',
              elementType: 'geometry',
              stylers: [{color: '#263c3f'}]
            },
            {
              featureType: 'poi.park',
              elementType: 'labels.text.fill',
              stylers: [{color: '#6b9a76'}]
            },
            {
              featureType: 'road',
              elementType: 'geometry',
              stylers: [{color: '#38414e'}]
            },
            {
              featureType: 'road',
              elementType: 'geometry.stroke',
              stylers: [{color: '#212a37'}]
            },
            {
              featureType: 'road',
              elementType: 'labels.text.fill',
              stylers: [{color: '#9ca5b3'}]
            },
            {
              featureType: 'road.highway',
              elementType: 'geometry',
              stylers: [{color: '#746855'}]
            },
            {
              featureType: 'road.highway',
              elementType: 'geometry.stroke',
              stylers: [{color: '#1f2835'}]
            },
            {
              featureType: 'road.highway',
              elementType: 'labels.text.fill',
              stylers: [{color: '#f3d19c'}]
            },
            {
              featureType: 'transit',
              elementType: 'geometry',
              stylers: [{color: '#2f3948'}]
            },
            {
              featureType: 'transit.station',
              elementType: 'labels.text.fill',
              stylers: [{color: '#d59563'}]
            },
            {
              featureType: 'water',
              elementType: 'geometry',
              stylers: [{color: '#17263c'}]
            },
            {
              featureType: 'water',
              elementType: 'labels.text.fill',
              stylers: [{color: '#515c6d'}]
            },
            {
              featureType: 'water',
              elementType: 'labels.text.stroke',
              stylers: [{color: '#17263c'}]
            }
          ], {'name': 'Night Mode'});

    var mapOptions = {
        zoom: 16,
        center: {'lat': 49.48052, 'lng': 8.48433},
        disableDefaultUI: true,
        mapTypeIds: ['styled_map']
    };

    maps = {
        'map': new google.maps.Map(document.getElementById('map'), mapOptions),
        'path': null,
        "startMarker": null,
        "endMarker": null,
        "locationMarker": null
    };

    maps['map'].mapTypes.set('styled_map', mapStyle);
    maps['map'].setMapTypeId('styled_map');
}

var mapIcons = {
    startMarker: {
        url: 'http://www.google.com/mapfiles/dd-start.png'
    },
    endMarker: {
        url: 'http://www.google.com/mapfiles/dd-end.png'
    },
    locationMarker: {
        url: 'http://labs.google.com/ridefinder/images/mm_20_green.png'
    }
}

function updateLocation(lat, lon) {
    updateMarker(lat, lon, 'locationMarker');
}

function updatePath(p) {
    // initialize path object
    if (maps['path'] == null) {
        maps['path'] = new google.maps.Polyline({
            map: maps['map'],
            strokeColor: '#FF0000',
            strokeOpacity: 1.0,
            strokeWeight: 2,
            path: new google.maps.MVCArray()
        });
    }

    let mapBounds = new google.maps.LatLngBounds();
    let path = new google.maps.MVCArray();

    for (let i = 0; i < p.length; ++i) {
        var point = new google.maps.LatLng(p[i][0], p[i][1]);
        path.push(point);
        mapBounds.extend(point);

        if (i === 0) {
            updateMarker(p[i][0], p[i][1], 'startMarker');
        }

        if (i === p.length - 1) {
            updateMarker(p[i][0], p[i][1], 'endMarker');
        }
    }

    maps['path'].setPath(path);
}

function updateMarker(lat, lon, marker) {
    // initialize location marker, if there is none
    if (maps[marker] == null) {
        maps[marker] = new google.maps.Marker();
    }

    var newLocation = new google.maps.LatLng(lat, lon);

    maps[marker].setOptions({
        icon: mapIcons[marker],
        draggable: false,
        map: maps['map'],
        position: newLocation
    });

    maps['map'].setZoom(16);
    maps['map'].panTo(newLocation);
}

