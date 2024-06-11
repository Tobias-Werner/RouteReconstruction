from tachograph import *


def do_worker(track_id_list, worker_id):
    while True:

        try:
            track_id = track_id_list.pop()

            with get_session() as session:

                try:

                    track_geom = get_track_geom(session, track_id)
                    driven_distance = get_track_length(session, track_id) / 1000

                    logging.info(
                        "Processing {}, Driven distance: {:.2f}, Rest: {}".format(track_id, driven_distance,
                                                                                  len(track_id_list)))

                    start_point = Point(track_geom.coords[0][0], track_geom.coords[0][1])
                    end_point = Point(track_geom.coords[-1][0], track_geom.coords[-1][1])

                    clip_network_ellipse(session, start_point, end_point, track_geom.length)

                    start_point_id = integrate_point_to_network(session, start_point)
                    end_point_id = integrate_point_to_network(session, end_point)

                    # further_nodes_available = True
                    # while further_nodes_available:
                    #     further_nodes_available = contract_network(session, (start_point_id, end_point_id))

                    G = load_network(session)

                    # G = reduce_nodes(session, G, start_point_id, end_point_id, driven_distance)

                    shortest_path_geom = calculate_shortest_path(session, G, start_point, start_point_id,
                                                                 end_point_id)
                    fastest_path_geom = calculate_fastest_path(session, G, start_point, start_point_id,
                                                               end_point_id)

                    frechet_dist_shortest = frechet_distance(shortest_path_geom, track_geom, 0.25)
                    frechet_dist_fastest = frechet_distance(fastest_path_geom, track_geom, 0.25)

                    session.add(
                        RouteP2PResults(
                            track_id=track_id,
                            type='shortest',
                            frechet_dist=frechet_dist_shortest,
                            geom_way=from_shape(shortest_path_geom, 25832)
                        )
                    )

                    session.add(
                        RouteP2PResults(
                            track_id=track_id,
                            type='fastest',
                            frechet_dist=frechet_dist_fastest,
                            geom_way=from_shape(fastest_path_geom, 25832)
                        )
                    )

                    G.clear()
                    session.flush()
                    session.commit()
                    session.close()
                    gc.collect()


                except Exception as e:
                    logging.error("Fehler {}: {}".format(track_id, e))

        except IndexError:
            logging.info("No item in list. Worker {} stopped.".format(worker_id))
            break


def do():
    # track_id = '5aee080644ea8508c5e70523'
    # track_id = '5207b9d6e4b058cd3d6683f0' # -> Bug Report pgrouting?
    # track_ids = ['574fcbfbe4b09078f97d73cc']

    # track_ids = ['577b556fe4b0ea24643a61de']

    # track_ids = ['578e8a60e4b086b281b46b19']

    track_ids = get_cleansed_track_ids(min_length_m=5000, max_length_m=10000)

    logging.info("Found {} tracks".format(len(track_ids)))

    # track_ids = ['640782635244bc763c99ef5f']

    manager = Manager()
    track_id_list = manager.list(track_ids)

    # with get_session() as session:
    #     session.query(RouteP2PResults).delete()
    #     session.commit()

    MultiprocessTask(do_worker, [track_id_list], num_workers=12).start()


if __name__ == "__main__":
    do()
