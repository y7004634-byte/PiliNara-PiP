import UIKit

final class BridgeViewController: UIViewController {
    private let titleLabel = UILabel()
    private let detailLabel = UILabel()
    private var lastURL: URL?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        titleLabel.text = "581 座標橋"
        titleLabel.font = .boldSystemFont(ofSize: 24)
        titleLabel.textAlignment = .center
        detailLabel.text = "等待 Uber 導航座標…\n這個 App 不讀定位、不連網。"
        detailLabel.font = .systemFont(ofSize: 16)
        detailLabel.textAlignment = .center
        detailLabel.numberOfLines = 0
        let stack = UIStackView(arrangedSubviews: [titleLabel, detailLabel])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 28),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -28)
        ])
    }

    func receive(_ url: URL, launchKind: String) {
        guard lastURL != url else { return }
        lastURL = url
        do {
            let destination = try UberWazeDestination.parse(url)
            detailLabel.text = String(format: "收到 Uber 座標\n%.7f, %.7f\n正在交給 Door Map…",
                                      destination.lat, destination.lng)
            UIApplication.shared.open(destination.door581URL, options: [:]) { [weak self] ok in
                DispatchQueue.main.async {
                    self?.detailLabel.text = ok
                        ? String(format: "已交給 Door Map\n%.7f, %.7f", destination.lat, destination.lng)
                        : "找不到可接收 door581:// 的 Door Map。"
                }
            }
        } catch {
            detailLabel.text = "收到的網址不是有效 Uber/Waze 台灣導航座標。"
        }
    }
}
