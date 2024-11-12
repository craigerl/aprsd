from aprsd import plugin
from aprsd.client import stats as client_stats
from aprsd.packets import packet_list, seen_list, tracker, watch_list
from aprsd.stats import app, collector
from aprsd.threads import aprsd


# Create the collector and register all the objects
# that APRSD has that implement the stats protocol
stats_collector = collector.Collector()
stats_collector.register_producer(app.APRSDStats)
stats_collector.register_producer(packet_list.PacketList)
stats_collector.register_producer(watch_list.WatchList)
stats_collector.register_producer(tracker.PacketTrack)
stats_collector.register_producer(plugin.PluginManager)
stats_collector.register_producer(aprsd.APRSDThreadList)
stats_collector.register_producer(client_stats.APRSClientStats)
stats_collector.register_producer(seen_list.SeenList)
