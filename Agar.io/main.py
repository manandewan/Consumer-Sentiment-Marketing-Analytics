import argparse
import sys
import os
import time

from training.train import PPOTrainer
from visualizer.server import VisualizerServer


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Deep RL Agar.io System with Self-Play")
    parser.add_argument("--train", action="store_true", help="Run Recurrent PPO Self-Play Training Loop")
    parser.add_argument("--duration", type=int, default=2000, help="Total training duration in seconds")
    parser.add_argument("--visualize", action="store_true", help="Launch Web Visualizer Dashboard & Streaming Server")
    parser.add_argument("--num-arenas", type=int, default=4, help="Number of parallel game arenas")
    parser.add_argument("--timesteps", type=int, default=1000, help="Number of training iterations/iterations")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP dashboard port")
    parser.add_argument("--ws-port", type=int, default=8081, help="WebSocket streaming port")

    args = parser.parse_args()

    if args.visualize:
        print(f"🚀 Starting Agar.io MARL Visualizer Dashboard on http://localhost:{args.http_port}...")
        server = VisualizerServer(http_port=args.http_port, ws_port=args.ws_port)
        server.start()

    elif args.train:
        print(f"🔥 Starting Recurrent PPO Training across {args.num_arenas} parallel arenas for {args.duration}s...", flush=True)
        trainer = PPOTrainer(num_arenas=args.num_arenas)
        start_time = time.time()
        iter_num = 0

        with open("training.log", "w") as log_file:
            log_file.write(f"=== Multi-Generation MARL PPO Training Started at {time.ctime()} ===\n")
            log_file.flush()

            while (time.time() - start_time) < args.duration:
                iter_num += 1
                stats = trainer.train_iteration(iter_num)
                elapsed = time.time() - start_time
                log_line = (
                    f"Gen {(iter_num // 20):02d} | Iter {stats['iter']:04d} | Elapsed: {elapsed:6.1f}s / {args.duration}s | "
                    f"Mean Reward: {stats['mean_reward']:+7.2f} | FPS: {stats['fps']:6.1f} | Policy Loss: {stats['policy_loss']:.4f}"
                )
                print(log_line, flush=True)
                log_file.write(log_line + "\n")
                log_file.flush()

                # Always ensure best_model.pt exists
                best_path = os.path.join(trainer.league.checkpoint_dir, "best_model.pt")
                if not os.path.exists(best_path):
                    torch.save(trainer.model.state_dict(), best_path)

        print(f"✅ Multi-generation training completed after {iter_num} iterations!", flush=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
